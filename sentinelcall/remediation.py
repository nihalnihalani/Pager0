"""Production remediation execution backends."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from sentinelcall.config import (
    GITHUB_REPO,
    GITHUB_ROLLBACK_REF,
    GITHUB_ROLLBACK_WORKFLOW_ID,
    GITHUB_TOKEN,
    REMEDIATION_WEBHOOK_SECRET,
    REMEDIATION_WEBHOOK_URL,
)
from sentinelcall.security import compute_hmac_sha256

logger = logging.getLogger(__name__)


class RemediationExecutor:
    """Execute a real remediation action through configured backends."""

    def build_plan(self, incident: dict[str, Any]) -> dict[str, Any]:
        causal_pr = incident.get("causal_pr", {}) or {}
        pr_number = causal_pr.get("pr_number")
        return {
            "type": "github_pr_rollback",
            "service": incident.get("service"),
            "incident_id": incident.get("incident_id"),
            "pr_number": pr_number,
            "description": incident.get("recommended_action", ""),
        }

    def execute(self, incident: dict[str, Any]) -> dict[str, Any]:
        plan = self.build_plan(incident)
        if not plan.get("pr_number"):
            return {
                "success": False,
                "status": "failed",
                "backend": None,
                "error": "No causal PR was identified for remediation.",
                "plan": plan,
            }

        if GITHUB_TOKEN and GITHUB_REPO and GITHUB_ROLLBACK_WORKFLOW_ID:
            return self._dispatch_github_workflow(plan)

        if REMEDIATION_WEBHOOK_URL:
            return self._dispatch_remediation_webhook(plan)

        return {
            "success": False,
            "status": "failed",
            "backend": None,
            "error": (
                "No remediation backend configured. Set GITHUB_ROLLBACK_WORKFLOW_ID "
                "for GitHub Actions or REMEDIATION_WEBHOOK_URL for an external executor."
            ),
            "plan": plan,
        }

    def _dispatch_github_workflow(self, plan: dict[str, Any]) -> dict[str, Any]:
        url = (
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/"
            f"{GITHUB_ROLLBACK_WORKFLOW_ID}/dispatches"
        )
        payload = {
            "ref": GITHUB_ROLLBACK_REF,
            "inputs": {
                "incident_id": str(plan["incident_id"]),
                "service": str(plan["service"]),
                "pr_number": str(plan["pr_number"]),
                "action": str(plan["description"]),
            },
        }
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("GitHub rollback workflow dispatch failed: %s", exc)
            return {
                "success": False,
                "status": "failed",
                "backend": "github_actions",
                "error": str(exc),
                "plan": plan,
            }

        return {
            "success": True,
            "status": "dispatched",
            "backend": "github_actions",
            "workflow_id": GITHUB_ROLLBACK_WORKFLOW_ID,
            "ref": GITHUB_ROLLBACK_REF,
            "requested_at": time.time(),
            "plan": plan,
        }

    def _dispatch_remediation_webhook(self, plan: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "incident_id": plan["incident_id"],
            "service": plan["service"],
            "pr_number": plan["pr_number"],
            "action": plan["description"],
        }
        body = requests.models.complexjson.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if REMEDIATION_WEBHOOK_SECRET:
            headers["X-Webhook-Signature"] = compute_hmac_sha256(
                REMEDIATION_WEBHOOK_SECRET,
                body,
            )

        try:
            response = requests.post(
                REMEDIATION_WEBHOOK_URL,
                data=body,
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            response_payload = response.json() if response.content else {}
        except requests.RequestException as exc:
            logger.error("Remediation webhook dispatch failed: %s", exc)
            return {
                "success": False,
                "status": "failed",
                "backend": "webhook",
                "error": str(exc),
                "plan": plan,
            }
        except ValueError:
            response_payload = {}

        return {
            "success": True,
            "status": "accepted",
            "backend": "webhook",
            "response": response_payload,
            "requested_at": time.time(),
            "plan": plan,
        }
