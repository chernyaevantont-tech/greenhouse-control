"""Dashboard configuration: broker address, topic names, rolling-window size."""

import os

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

# Rolling window size: 96 steps/day × 6 days = 576
WINDOW_SIZE = 576

# MQTT topics
TOPIC_TELEMETRY = "greenhouse/telemetry"
TOPIC_ACTION_APPROVED = "greenhouse/action/approved"
TOPIC_OOD_METRICS = "greenhouse/ood/metrics"
TOPIC_SUPERVISOR_VERDICT = "greenhouse/supervisor/verdict"
