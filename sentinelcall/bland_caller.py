"""Bland AI outbound incident call for SentinelCall."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BLAND_API_KEY = os.environ['BLAND_API_KEY']


def make_incident_call(phone_number: str, incident: dict) -> dict:
    """
    Place an outbound Bland AI call to brief the on-call engineer.
    Uses interactive prompting so the engineer can ask questions or approve remediation.
    """
    service = incident['service']
    error_rate = incident.get('error_rate_pct', 'unknown')
    latency = incident.get('latency_ms', 'unknown')
    root_cause = incident.get('root_cause', 'under investigation')
    severity = incident.get('severity', 'critical')

    task = f"""You are SentinelCall, an autonomous incident response agent at a tech company.

You have detected a {severity} incident. Here are the details:
- Service: {service}
- Error rate: {error_rate}%
- Latency: {latency}ms
- Root cause: {root_cause}

Your job:
1. Greet the engineer and immediately brief them on the incident in 2-3 sentences.
2. Ask if they want more details or if they authorize you to begin automated remediation.
3. If they ask questions, answer using the incident data above.
4. If they say yes or approve, confirm that remediation is starting and you will publish an incident report.
5. If they say no or decline, acknowledge and say the incident is being escalated to the VP of Engineering.
6. Keep the call under 2 minutes. Be professional, calm, and direct — this is an emergency."""

    response = requests.post(
        'https://api.bland.ai/v1/calls',
        headers={'authorization': BLAND_API_KEY},
        json={
            'phone_number': phone_number,
            'task': task,
            'voice': 'mason',
            'wait_for_greeting': True,
            'record': True,
            'metadata': {'incident_id': incident.get('incident_id', 'INC-001')},
        },
    )
    return response.json()


def get_call_status(call_id: str) -> dict:
    """Fetch status and transcript for a completed call."""
    response = requests.get(
        f'https://api.bland.ai/v1/calls/{call_id}',
        headers={'authorization': BLAND_API_KEY},
    )
    return response.json()


def parse_authorization(transcript: str) -> bool:
    """Parse engineer's verbal authorization from call transcript."""
    approval_phrases = ['yes', 'approved', 'go ahead', 'proceed', 'authorize', 'do it', 'confirm']
    transcript_lower = transcript.lower()
    return any(phrase in transcript_lower for phrase in approval_phrases)
