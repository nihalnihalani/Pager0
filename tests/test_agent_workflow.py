import os
import tempfile
import unittest
from unittest.mock import Mock, patch


_DB_FILE = tempfile.NamedTemporaryFile(prefix="pager0-tests-", suffix=".db", delete=False)
_DB_FILE.close()
os.environ["PAGER0_DB_PATH"] = _DB_FILE.name

from sentinelcall.agent import SentinelCallAgent
from sentinelcall.persistence import store
from sentinelcall.security import compute_hmac_sha256, verify_hmac_sha256


class AgentWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        with store._lock:
            store._conn.execute("DELETE FROM incidents")
            store._conn.execute("DELETE FROM webhook_events")
            store._conn.commit()
        self.agent = SentinelCallAgent()
        self.agent.gateway.llm_call = Mock(
            return_value={"response": "Root cause analysis", "model": "test-model"}
        )
        self.agent.dynamic_connectors.dynamically_investigate = Mock(
            return_value={"status": "mock"}
        )
        self.agent.dynamic_connectors.get_investigation_summary = Mock(
            return_value={"total_connectors_created": 1, "connectors": []}
        )
        self.agent.macroscope.identify_causal_pr = Mock(
            return_value={
                "pr_number": 47,
                "pr_title": "Rollback pool change",
                "confidence": "high",
                "explanation": "PR #47 caused the pool exhaustion.",
            }
        )
        self.agent.ciba.initiate_ciba_approval = Mock(
            return_value={
                "auth_req_id": "ciba-test-1",
                "expires_in": 300,
                "interval": 5,
                "status": "pending",
                "source": "simulated",
            }
        )
        self.agent.ciba.complete_ciba_from_voice = Mock(
            return_value={
                "auth_req_id": "ciba-test-1",
                "access_token": "auth0-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "status": "approved",
                "source": "simulated",
            }
        )
        self.agent.token_vault.get_token = Mock(
            return_value={"access_token": "ghs_test", "service": "github", "source": "mock"}
        )
        self.agent.remediation.execute = Mock(
            return_value={
                "success": True,
                "status": "dispatched",
                "backend": "github_actions",
                "plan": {"pr_number": 47},
            }
        )
        self.agent.report_publisher.publish_incident_report = Mock(
            return_value={
                "executive_report": {"url": "https://ghost.example/executive"},
                "engineering_report": {"url": "https://ghost.example/engineering"},
            }
        )

    async def test_incident_waits_for_approval_then_resumes(self) -> None:
        with patch("sentinelcall.agent.create_pathway", return_value={"pathway_id": "pathway-1"}), patch(
            "sentinelcall.agent.make_incident_call",
            return_value={"status": "success", "call_id": "call-1"},
        ), patch(
            "sentinelcall.agent.get_call_transcript",
            return_value={"concatenated_transcript": "Engineer approved the rollback."},
        ):
            started = await self.agent.run_incident_response(
                service="payment-service",
                incident_type="payment_service_error",
            )
            self.assertEqual(started["status"], "awaiting_approval")
            self.assertEqual(started["ciba_auth_req_id"], "ciba-test-1")

            approval = await self.agent.approve_incident_from_voice(
                "ciba-test-1",
                call_id="call-1",
                transcript_data={"concatenated_transcript": "Engineer approved the rollback."},
            )
            self.assertEqual(approval["status"], "approved")

            await self.agent.wait_for_active_tasks()

        incidents = self.agent.get_incident_history()
        self.assertEqual(len(incidents), 1)
        final = incidents[0]
        self.assertEqual(final["status"], "resolved")
        self.assertTrue(final["remediation"]["success"])
        self.assertEqual(final["reports"]["executive_url"], "https://ghost.example/executive")
        self.assertEqual(final["steps"]["auth0_ciba"]["vault_service"], "github")

    def test_hmac_verification(self) -> None:
        body = b'{"incident_id":"INC-1"}'
        secret = "super-secret"
        signature = compute_hmac_sha256(secret, body)
        self.assertTrue(verify_hmac_sha256(secret, body, signature))
        self.assertTrue(verify_hmac_sha256(secret, body, f"sha256={signature}"))
        self.assertFalse(verify_hmac_sha256(secret, body, "bad-signature"))


if __name__ == "__main__":
    unittest.main()
