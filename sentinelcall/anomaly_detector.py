"""Statistical anomaly detection on infrastructure metrics."""

THRESHOLDS = {
    'error_rate_pct': 5.0,   # >5% = anomaly
    'latency_ms': 500.0,      # >500ms = anomaly
    'cpu_pct': 80.0,          # >80% = anomaly
}


def detect_anomalies(metrics: list[dict]) -> list[dict]:
    """
    Detect anomalies in infrastructure metrics using static thresholds.
    Returns list of anomaly dicts, empty if all clear.
    """
    anomalies = []
    for m in metrics:
        service = m['service']
        for field, threshold in THRESHOLDS.items():
            value = m.get(field, 0)
            if value > threshold:
                severity = 'critical' if value > threshold * 2 else 'warning'
                anomalies.append({
                    'service': service,
                    'metric': field,
                    'value': value,
                    'threshold': threshold,
                    'severity': severity,
                })
    return anomalies
