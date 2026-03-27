"""SentinelCall — main agent orchestration loop."""
import os
import asyncio
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

from airbyte_monitor import ingest_mock_infra_metrics, dynamically_investigate
from anomaly_detector import detect_anomalies
from bland_caller import make_incident_call

load_dotenv()

ON_CALL_PHONE = os.environ.get('ON_CALL_PHONE', '+16502849109')


async def run_agent(inject_anomaly: bool = False) -> dict:
    """
    Full incident response pipeline:
    1. Ingest metrics via Airbyte
    2. Detect anomalies
    3. Dynamically investigate with new connectors
    4. Call on-call engineer via Bland AI
    """
    incident_id = f'INC-{uuid.uuid4().hex[:6].upper()}'
    print(f'\n[{incident_id}] SentinelCall agent starting...')

    # Step 1: Ingest metrics
    print(f'[{incident_id}] Ingesting infrastructure metrics via Airbyte...')
    metrics = ingest_mock_infra_metrics(inject_anomaly=inject_anomaly)

    # Step 2: Detect anomalies
    print(f'[{incident_id}] Running anomaly detection...')
    anomalies = detect_anomalies(metrics)

    if not anomalies:
        print(f'[{incident_id}] All systems nominal. No action required.')
        return {'status': 'nominal', 'incident_id': incident_id}

    print(f'[{incident_id}] {len(anomalies)} anomaly(ies) detected!')
    for a in anomalies:
        print(f'  - {a["service"]}: {a["metric"]}={a["value"]} (threshold={a["threshold"]}, severity={a["severity"]})')

    # Find the worst anomaly to build the incident context
    critical = [a for a in anomalies if a['severity'] == 'critical']
    primary = critical[0] if critical else anomalies[0]

    # Find the full metric record for the affected service
    service_metrics = next((m for m in metrics if m['service'] == primary['service']), {})

    # Step 3: Dynamic investigation — spin up a new Airbyte connector
    print(f'[{incident_id}] Launching dynamic Airbyte investigation for {primary["service"]}...')
    investigation = dynamically_investigate('api_latency_spike', {'repo': 'sentinelcall'})
    root_cause = investigation['finding']
    print(f'[{incident_id}] Root cause identified: {root_cause}')

    # Step 4: Call on-call engineer via Bland AI
    incident_context = {
        'incident_id': incident_id,
        'service': primary['service'],
        'error_rate_pct': service_metrics.get('error_rate_pct', primary['value']),
        'latency_ms': service_metrics.get('latency_ms', 'N/A'),
        'severity': primary['severity'],
        'root_cause': root_cause,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }

    print(f'[{incident_id}] Calling on-call engineer at {ON_CALL_PHONE}...')
    call_result = make_incident_call(ON_CALL_PHONE, incident_context)

    if call_result.get('status') == 'success':
        call_id = call_result['call_id']
        print(f'[{incident_id}] Call queued successfully. call_id={call_id}')
    else:
        print(f'[{incident_id}] Call failed: {call_result}')
        call_id = None

    return {
        'status': 'incident_detected',
        'incident_id': incident_id,
        'anomalies': anomalies,
        'root_cause': root_cause,
        'call_id': call_id,
        'call_status': call_result.get('status'),
    }


if __name__ == '__main__':
    result = asyncio.run(run_agent(inject_anomaly=True))
    print(f'\nAgent result: {result}')
