"""Pager0 incident orchestrator with persisted state and approval gating."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from sentinelcall.airbyte_dynamic import DynamicConnectorManager
from sentinelcall.airbyte_monitor import AirbyteMonitor
from sentinelcall.anomaly_detector import AnomalyDetector
from sentinelcall.auth0_ciba import CIBAManager
from sentinelcall.auth0_vault import TokenVault
from sentinelcall.bland_caller import get_call_transcript, make_incident_call
from sentinelcall.bland_pathway import create_pathway
from sentinelcall.config import ON_CALL_ENGINEER_ID, WEBHOOK_BASE_URL
from sentinelcall.ghost_incident_reports import IncidentReportPublisher
from sentinelcall.ghost_publisher import GhostPublisher
from sentinelcall.ghost_webhooks import setup_ghost_webhooks
from sentinelcall.macroscope_rca import MacroscopeAnalyzer
from sentinelcall.mock_infra import MockInfrastructure
from sentinelcall.overmind_setup import OvermindTracer
from sentinelcall.persistence import store
from sentinelcall.remediation import RemediationExecutor
from sentinelcall.truefoundry_gateway import TrueFoundryGateway
from sentinelcall.truefoundry_guardrails import GuardrailsConfig

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {
    "investigating",
    "responding",
    "awaiting_approval",
    "approved",
    "remediating",
    "publishing_reports",
    "monitoring",
}


class SentinelCallAgent:
    """Orchestrates the incident lifecycle from detection through remediation."""

    def __init__(self) -> None:
        self.infra = MockInfrastructure()
        self.airbyte = AirbyteMonitor()
        self.dynamic_connectors = DynamicConnectorManager()
        self.anomaly_detector = AnomalyDetector()

        self.token_vault = TokenVault()
        self.ciba = CIBAManager()

        self.gateway = TrueFoundryGateway()
        self.guardrails = GuardrailsConfig()

        self.ghost = GhostPublisher()
        self.report_publisher = IncidentReportPublisher(self.ghost)
        self.macroscope = MacroscopeAnalyzer()
        self.tracer = OvermindTracer()
        self.tracer.init()
        self.remediation = RemediationExecutor()

        self.store = store
        self.incidents: list[dict[str, Any]] = self.store.list_incidents()
        self._incident_index = {
            incident["incident_id"]: incident for incident in self.incidents
        }
        self.current_status = self._derive_current_status()
        self._event_subscribers: list[asyncio.Queue] = []
        self._background_tasks: dict[str, asyncio.Task[Any]] = {}

        logger.info("Pager0 agent initialized with %d persisted incidents", len(self.incidents))

    # ------------------------------------------------------------------
    # Subscription / persistence helpers
    # ------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._event_subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._event_subscribers.remove(q)
        except ValueError:
            pass

    async def _broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        payload = {"event": event_type, "data": data, "timestamp": time.time()}
        for q in list(self._event_subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def _derive_current_status(self) -> str:
        for incident in sorted(
            self.incidents,
            key=lambda item: item.get("updated_at", item.get("started_at", 0)),
            reverse=True,
        ):
            status = incident.get("status", "idle")
            if status in ACTIVE_STATUSES:
                return status
        return "idle"

    def _save_incident(self, incident: dict[str, Any]) -> dict[str, Any]:
        incident["updated_at"] = time.time()
        self._incident_index[incident["incident_id"]] = incident
        self.store.upsert_incident(incident)
        self.incidents = sorted(
            self._incident_index.values(),
            key=lambda item: item.get("started_at", item.get("created_at", 0)),
        )
        self.current_status = self._derive_current_status()
        return incident

    def _load_incident(self, incident_id: str) -> dict[str, Any] | None:
        if incident_id in self._incident_index:
            return self._incident_index[incident_id]
        incident = self.store.get_incident(incident_id)
        if incident is not None:
            self._incident_index[incident_id] = incident
            self.incidents = sorted(
                self._incident_index.values(),
                key=lambda item: item.get("started_at", item.get("created_at", 0)),
            )
        self.current_status = self._derive_current_status()
        return incident

    async def wait_for_active_tasks(self) -> None:
        tasks = [task for task in self._background_tasks.values() if not task.done()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ------------------------------------------------------------------
    # Incident creation / approval
    # ------------------------------------------------------------------

    async def run_incident_response(
        self,
        service: str | None = None,
        incident_type: str | None = None,
        metrics: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run the pre-approval half of the pipeline and stop at the human gate."""
        service = service or "payment-service"
        incident_type = incident_type or "payment_service_error"
        incident_id = f"INC-{uuid.uuid4().hex[:8]}"
        pipeline_start = time.time()
        incident_record: dict[str, Any] = {
            "incident_id": incident_id,
            "service": service,
            "incident_type": incident_type,
            "started_at": pipeline_start,
            "status": "investigating",
            "approval_state": "pending",
            "steps": {},
            "external_metrics": metrics is not None,
        }
        self._save_incident(incident_record)

        await self._broadcast("incident_start", {"incident_id": incident_id, "service": service})

        try:
            # Step 1: collect metrics
            step_start = time.time()
            if metrics is None:
                self.infra.trigger_incident(service=service, incident_type=incident_type)
                metrics = self.infra.get_metrics()
                metrics_source = "mock_infra"
            else:
                metrics_source = "external_payload"
            incident_record["steps"]["metrics"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "services_monitored": len(metrics),
                "source": metrics_source,
            }
            self.tracer.record_decision(
                step="metrics_collection",
                input_data={"service": service, "incident_type": incident_type},
                output_data={"services": len(metrics), "source": metrics_source},
                model_used=metrics_source,
            )
            self._save_incident(incident_record)
            await self._broadcast("step_complete", {"step": "metrics_collection"})
            await asyncio.sleep(1.0)

            # Step 2: anomaly detection
            step_start = time.time()
            anomalies = self.anomaly_detector.detect_anomalies(metrics)
            severity = self.anomaly_detector.classify_severity(anomalies)
            anomaly_text = self.anomaly_detector.format_for_diagnosis(anomalies)
            incident_record["severity"] = (
                f"SEV-{'1' if severity == 'critical' else '2' if severity == 'warning' else '3'}"
            )
            incident_record["anomaly_count"] = len(anomalies)
            incident_record["steps"]["anomaly_detection"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "anomalies_found": len(anomalies),
                "severity": severity,
            }
            self.tracer.record_decision(
                step="anomaly_detection",
                input_data={"metrics_count": len(metrics)},
                output_data={"anomalies": len(anomalies), "severity": severity},
                model_used="statistical+threshold",
            )
            self._save_incident(incident_record)
            await self._broadcast(
                "step_complete",
                {"step": "anomaly_detection", "severity": severity, "anomalies": len(anomalies)},
            )
            await asyncio.sleep(1.0)

            # Step 3: diagnosis
            step_start = time.time()
            is_safe, reason = self.guardrails.check_input(anomaly_text)
            if is_safe:
                diagnosis_result = self.gateway.llm_call(
                    prompt=anomaly_text,
                    severity=severity,
                    system_prompt=(
            "You are Pager0, an autonomous SRE agent. "
                        "Analyze these anomalies and provide root cause, "
                        "impact assessment, and remediation steps."
                    ),
                )
                diagnosis_text = diagnosis_result["response"]
                diagnosis_text, redactions = self.guardrails.check_output(diagnosis_text)
                model_used = diagnosis_result["model"]
            else:
                diagnosis_text = f"Guardrails blocked input: {reason}"
                model_used = "blocked"
                redactions = []
            incident_record["diagnosis"] = diagnosis_text
            incident_record["model_used"] = model_used
            incident_record["steps"]["llm_diagnosis"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "model": model_used,
                "severity_tier": severity,
                "redactions": len(redactions),
            }
            self.tracer.record_decision(
                step="llm_diagnosis",
                input_data={"anomaly_text_len": len(anomaly_text)},
                output_data={"model": model_used, "response_len": len(diagnosis_text)},
                model_used=model_used,
            )
            self._save_incident(incident_record)
            await self._broadcast("step_complete", {"step": "llm_diagnosis", "model": model_used})
            await asyncio.sleep(1.0)

            # Step 4: dynamic investigation
            step_start = time.time()
            investigation = self.dynamic_connectors.dynamically_investigate(
                incident_type=incident_type,
                context={"service": service},
            )
            connector_summary = self.dynamic_connectors.get_investigation_summary()
            incident_record["steps"]["dynamic_investigation"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "connectors_created": connector_summary["total_connectors_created"],
                "status": investigation.get("status"),
            }
            self.tracer.record_decision(
                step="dynamic_airbyte_investigation",
                input_data={"incident_type": incident_type},
                output_data={"connectors": connector_summary["total_connectors_created"]},
                model_used="airbyte_dynamic",
            )
            self._save_incident(incident_record)
            await self._broadcast(
                "step_complete",
                {
                    "step": "dynamic_investigation",
                    "connectors_created": connector_summary["total_connectors_created"],
                },
            )
            await asyncio.sleep(1.0)

            # Step 5: root cause analysis
            step_start = time.time()
            macroscope_result = self.macroscope.identify_causal_pr(
                {
                    "incident_id": incident_id,
                    "service": service,
                    "severity": incident_record["severity"],
                    "description": diagnosis_text[:200],
                    "symptoms": f"{len(anomalies)} anomalies detected",
                }
            )
            incident_record["causal_pr"] = {
                "pr_number": macroscope_result.get("pr_number"),
                "pr_title": macroscope_result.get("pr_title"),
                "confidence": macroscope_result.get("confidence"),
            }
            incident_record["root_cause"] = macroscope_result.get("explanation", diagnosis_text)
            incident_record["steps"]["macroscope_rca"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "causal_pr": macroscope_result.get("pr_number"),
                "confidence": macroscope_result.get("confidence"),
            }
            self.tracer.record_decision(
                step="macroscope_rca",
                input_data={"incident_id": incident_id},
                output_data={
                    "pr": macroscope_result.get("pr_number"),
                    "confidence": macroscope_result.get("confidence"),
                },
                model_used="macroscope+llm",
            )
            self._save_incident(incident_record)
            await self._broadcast(
                "step_complete",
                {"step": "macroscope_rca", "causal_pr": macroscope_result.get("pr_number")},
            )
            await asyncio.sleep(1.0)

            # Step 6: approval gate
            step_start = time.time()
            pr_number = incident_record["causal_pr"].get("pr_number")
            recommended_action = (
                f"Roll back PR #{pr_number} for {service} via the configured remediation backend"
                if pr_number
                else f"Execute the configured remediation plan for {service}"
            )
            ciba_result = self.ciba.initiate_ciba_approval(
                engineer_id=ON_CALL_ENGINEER_ID,
                action=recommended_action,
            )
            auth_req_id = ciba_result.get("auth_req_id", "")
            incident_record["ciba_auth_req_id"] = auth_req_id
            incident_record["recommended_action"] = recommended_action
            incident_record["approval_deadline_at"] = time.time() + ciba_result.get("expires_in", 300)
            incident_record["steps"]["auth0_ciba"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "auth_req_id": auth_req_id,
                "source": ciba_result.get("source"),
            }
            self.tracer.record_decision(
                step="auth0_ciba_initiation",
                input_data={"engineer": ON_CALL_ENGINEER_ID, "action": recommended_action},
                output_data={"auth_req_id": auth_req_id},
                model_used="auth0",
            )
            self._save_incident(incident_record)
            await self._broadcast(
                "step_complete",
                {"step": "auth0_ciba", "auth_req_id": auth_req_id},
            )
            await asyncio.sleep(1.0)

            # Step 7: phone call
            step_start = time.time()
            pathway_result = create_pathway(
                {
                    "service": service,
                    "severity": incident_record["severity"],
                    "description": diagnosis_text[:300],
                    "root_cause": incident_record["root_cause"][:300],
                    "recommended_action": recommended_action,
                    "engineer_id": ON_CALL_ENGINEER_ID,
                    "auth_req_id": auth_req_id,
                }
            )
            call_result = make_incident_call(
                incident_context={
                    "incident_id": incident_id,
                    "service": service,
                    "severity": incident_record["severity"],
                    "description": diagnosis_text[:300],
                    "root_cause": incident_record["root_cause"][:300],
                    "recommended_action": recommended_action,
                    "engineer_id": ON_CALL_ENGINEER_ID,
                    "ciba_auth_req_id": auth_req_id,
                },
                pathway_id=pathway_result.get("pathway_id"),
                ciba_auth_req_id=auth_req_id,
            )
            incident_record["call_id"] = call_result.get("call_id", "unknown")
            incident_record["steps"]["bland_call"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "call_id": incident_record["call_id"],
                "pathway_id": pathway_result.get("pathway_id"),
                "call_status": call_result.get("status"),
                "mock": call_result.get("mock", False),
            }
            self.tracer.record_decision(
                step="bland_ai_phone_call",
                input_data={"pathway_id": pathway_result.get("pathway_id"), "engineer": ON_CALL_ENGINEER_ID},
                output_data={"call_id": incident_record["call_id"], "status": call_result.get("status")},
                model_used="bland_ai",
            )

            incident_record["status"] = "awaiting_approval"
            self._save_incident(incident_record)
            await self._broadcast(
                "step_complete",
                {"step": "bland_call", "call_id": incident_record["call_id"]},
            )
            await self._broadcast(
                "incident_pending_approval",
                {
                    "incident_id": incident_id,
                    "auth_req_id": auth_req_id,
                    "call_id": incident_record["call_id"],
                },
            )

        except Exception as exc:
            logger.exception("Incident response pipeline failed: %s", exc)
            incident_record["status"] = "failed"
            incident_record["error"] = str(exc)
            if not incident_record.get("external_metrics"):
                self.infra.resolve_incident()
            self._save_incident(incident_record)
            await self._broadcast("incident_error", {"incident_id": incident_id, "error": str(exc)})

        logger.info("Incident %s now in status %s", incident_id, incident_record["status"])
        return incident_record

    async def approve_incident_from_voice(
        self,
        auth_req_id: str,
        call_id: str | None = None,
        transcript_data: dict[str, Any] | None = None,
        approval_source: str = "voice",
    ) -> dict[str, Any]:
        """Complete the approval gate and schedule the post-approval pipeline."""
        incident_record = self.store.find_incident_by_auth_req_id(auth_req_id)
        if incident_record is None:
            return {
                "status": "failed",
                "message": f"No incident found for auth_req_id {auth_req_id}.",
            }

        self._incident_index[incident_record["incident_id"]] = incident_record
        if call_id:
            incident_record["call_id"] = call_id
        if transcript_data:
            incident_record["call_transcript"] = transcript_data

        if incident_record.get("status") in {"approved", "remediating", "publishing_reports", "resolved"}:
            return {
                "status": incident_record["status"],
                "incident_id": incident_record["incident_id"],
                "message": "Approval has already been processed for this incident.",
            }

        approval_result = self.ciba.complete_ciba_from_voice(auth_req_id)
        incident_record["approval"] = {
            "status": approval_result.get("status"),
            "source": approval_source,
            "processed_at": time.time(),
        }
        incident_record["steps"].setdefault("auth0_ciba", {}).update(
            {
                "approval_source": approval_source,
                "completion_status": approval_result.get("status"),
            }
        )

        if approval_result.get("status") != "approved":
            incident_record["status"] = (
                "awaiting_approval"
                if approval_result.get("status") == "pending"
                else "failed"
            )
            self._save_incident(incident_record)
            return {
                "status": approval_result.get("status", "failed"),
                "incident_id": incident_record["incident_id"],
                "message": approval_result.get(
                    "error_description",
                    "Approval did not complete successfully.",
                ),
            }

        access_token = approval_result.get("access_token")
        if access_token:
            self.token_vault.set_subject_token(access_token)
        vault_token = self.token_vault.get_token("github")

        incident_record["approved_at"] = time.time()
        incident_record["approval_state"] = "approved"
        incident_record["status"] = "approved"
        incident_record["steps"]["auth0_ciba"].update(
            {
                "approved_at": incident_record["approved_at"],
                "vault_service": vault_token.get("service"),
                "vault_source": vault_token.get("source"),
            }
        )
        self._save_incident(incident_record)
        await self._broadcast(
            "incident_approved",
            {
                "incident_id": incident_record["incident_id"],
                "auth_req_id": auth_req_id,
                "call_id": incident_record.get("call_id"),
            },
        )

        existing_task = self._background_tasks.get(incident_record["incident_id"])
        if existing_task is None or existing_task.done():
            self._background_tasks[incident_record["incident_id"]] = asyncio.create_task(
                self.resume_incident_after_approval(
                    incident_record["incident_id"],
                    transcript_data=transcript_data,
                )
            )

        return {
            "status": "approved",
            "incident_id": incident_record["incident_id"],
            "message": "Approval recorded. Remediation has started.",
        }

    async def resume_incident_after_approval(
        self,
        incident_id: str,
        transcript_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run remediation, report publication, and closure after approval."""
        incident_record = self._load_incident(incident_id)
        if incident_record is None:
            return {"status": "failed", "error": f"Incident {incident_id} not found."}

        if incident_record.get("status") not in {"approved", "remediation_failed"}:
            return incident_record

        try:
            incident_record["status"] = "remediating"
            self._save_incident(incident_record)
            await self._broadcast("remediation_started", {"incident_id": incident_id})

            # Step 8: remediation execution
            step_start = time.time()
            remediation_result = self.remediation.execute(incident_record)
            incident_record["remediation"] = remediation_result
            incident_record["steps"]["remediation"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "backend": remediation_result.get("backend"),
                "status": remediation_result.get("status"),
                "success": remediation_result.get("success", False),
            }
            self.tracer.record_decision(
                step="remediation_execution",
                input_data={"incident_id": incident_id, "service": incident_record.get("service")},
                output_data={
                    "success": remediation_result.get("success", False),
                    "backend": remediation_result.get("backend"),
                },
                model_used=remediation_result.get("backend", "remediation_executor"),
            )
            self._save_incident(incident_record)
            await self._broadcast(
                "step_complete",
                {
                    "step": "remediation",
                    "incident_id": incident_id,
                    "success": remediation_result.get("success", False),
                },
            )

            if not remediation_result.get("success"):
                incident_record["status"] = "remediation_failed"
                incident_record["error"] = remediation_result.get("error")
                self._save_incident(incident_record)
                await self._broadcast(
                    "incident_error",
                    {"incident_id": incident_id, "error": remediation_result.get("error", "Remediation failed")},
                )
                return incident_record

            if transcript_data is None and incident_record.get("call_id"):
                transcript_data = get_call_transcript(incident_record["call_id"])

            # Step 9: Ghost tiered reports
            incident_record["status"] = "publishing_reports"
            self._save_incident(incident_record)
            step_start = time.time()
            setup_ghost_webhooks(WEBHOOK_BASE_URL)

            metrics = self.infra.get_metrics()
            report_result = self.report_publisher.publish_incident_report(
                incident={
                    "incident_id": incident_id,
                    "service": incident_record["service"],
                    "severity": incident_record.get("severity", "SEV-2"),
                    "description": incident_record.get("diagnosis", "")[:500],
                    "started_at": incident_record["started_at"],
                    "status": "remediation_executed",
                },
                diagnosis={
                    "root_cause": incident_record.get("root_cause", "Under investigation"),
                    "metrics_snapshot": {
                        key: f"{value.get('error_rate', 0)}% error, {value.get('latency_ms', 0)}ms p99"
                        for key, value in metrics.items()
                        if key == incident_record["service"]
                    },
                    "airbyte_sources": [
                        connector.get("display_name", "unknown")
                        for connector in self.dynamic_connectors.get_investigation_summary().get("connectors", [])
                    ],
                    "remediation_steps": [
                        incident_record.get("recommended_action", "Execute configured remediation"),
                    ],
                    "macroscope_analysis": incident_record.get("causal_pr", {}),
                    "bland_transcript": (transcript_data or {}).get("concatenated_transcript", ""),
                    "overmind_trace": self.tracer.get_decision_trace(),
                    "eta_minutes": 5,
                    "action_taken": incident_record.get("recommended_action", ""),
                    "impact": "Elevated error rates affecting customer traffic",
                },
            )
            incident_record["reports"] = {
                "executive_url": report_result.get("executive_report", {}).get("url"),
                "engineering_url": report_result.get("engineering_report", {}).get("url"),
            }
            incident_record["steps"]["ghost_reports"] = {
                "duration_ms": round((time.time() - step_start) * 1000, 1),
                "executive_url": incident_record["reports"]["executive_url"],
                "engineering_url": incident_record["reports"]["engineering_url"],
            }
            self.tracer.record_decision(
                step="ghost_report_publishing",
                input_data={"incident_id": incident_id},
                output_data={"reports_published": 2},
                model_used="ghost_cms",
            )
            self._save_incident(incident_record)
            await self._broadcast("step_complete", {"step": "ghost_reports", "reports_published": 2})

            # Step 10: closeout / recovery verification
            if not incident_record.get("external_metrics"):
                self.infra.resolve_incident()
            verification_status = self.infra.get_service_status(incident_record["service"])
            incident_record["verification"] = {
                "service_status": verification_status,
                "checked_at": time.time(),
            }
            incident_record["resolved_at"] = time.time()
            incident_record["total_duration_seconds"] = round(
                incident_record["resolved_at"] - incident_record["started_at"],
                1,
            )
            incident_record["status"] = "resolved" if verification_status == "healthy" else "monitoring"
            incident_record["overmind_trace"] = self.tracer.get_decision_trace()
            incident_record["overmind_optimization"] = self.tracer.get_optimization_report()
            self.tracer.record_decision(
                step="incident_resolved",
                input_data={"incident_id": incident_id},
                output_data={
                    "duration_s": incident_record["total_duration_seconds"],
                    "verification_status": verification_status,
                },
                model_used="orchestrator",
            )
            self._save_incident(incident_record)
            await self._broadcast(
                "incident_resolved" if incident_record["status"] == "resolved" else "incident_monitoring",
                {
                    "incident_id": incident_id,
                    "duration_seconds": incident_record["total_duration_seconds"],
                    "status": incident_record["status"],
                },
            )
            return incident_record

        except Exception as exc:
            logger.exception("Post-approval incident flow failed: %s", exc)
            incident_record["status"] = "failed"
            incident_record["error"] = str(exc)
            self._save_incident(incident_record)
            await self._broadcast("incident_error", {"incident_id": incident_id, "error": str(exc)})
            return incident_record

    # ------------------------------------------------------------------
    # Status / history
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        active_incident = None
        for incident in reversed(self.incidents):
            if incident.get("status") in ACTIVE_STATUSES:
                active_incident = {
                    "incident_id": incident.get("incident_id"),
                    "status": incident.get("status"),
                    "service": incident.get("service"),
                }
                break

        pending_approvals = [
            incident["incident_id"]
            for incident in self.incidents
            if incident.get("status") == "awaiting_approval"
        ]
        return {
            "agent_status": self.current_status,
            "active_incident": active_incident,
            "pending_approvals": pending_approvals,
            "services": {
                service: self.infra.get_service_status(service)
                for service in self.infra._baselines
            },
            "total_incidents": len(self.incidents),
            "gateway_mode": self.gateway._mode,
            "token_vault_live": self.token_vault.is_live,
            "ciba_live": self.ciba.is_live,
            "guardrails": self.guardrails.get_guardrails_summary(),
            "overmind_url": self.tracer.get_dashboard_url(),
            "llm_usage": self.gateway.get_usage_stats(),
        }

    def get_incident_history(self) -> list[dict[str, Any]]:
        self.incidents = self.store.list_incidents()
        self._incident_index = {
            incident["incident_id"]: incident for incident in self.incidents
        }
        self.current_status = self._derive_current_status()
        return list(self.incidents)
