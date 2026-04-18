# GreeMQTT

Bridge Gree air conditioners to MQTT for integration with Home Assistant and other smart home platforms. Discovers devices automatically, retrieves parameters, and enables control via MQTT topics.

**Single-container, event-driven architecture** — no Redis, RabbitMQ, or docker-compose required.

## Features

- Automatic device discovery on the local network
- MQTT-based control for setting and retrieving device parameters
- Adaptive multi-tier polling (0.1s → 0.3s → 0.8s → 3s) based on activity
- Sub-second command response times (typically 50–150ms)
- Concurrent processing of multiple MQTT commands
- Immediate state publishing after parameter changes
- Configuration via environment variables or `.env` file
- Multi-platform Docker support (amd64, arm64, arm/v7)

## Quick Start

### Docker (Recommended)

```bash
docker run --env-file .env --network host --name greemqtt monteship/greemqtt:latest
```

`--network host` is required for UDP device discovery.

### Manual

```bash
git clone https://github.com/monteship/GreeMQTT.git
cd GreeMQTT
python -m pip install -e .
python -m GreeMQTT
```

## Configuration

Create a `.env` file:

```env
# Required
MQTT_BROKER=192.168.1.50

# Optional — Network
NETWORK=192.168.1.100,192.168.1.101  # Leave empty for auto-discovery

# Optional — MQTT
MQTT_PORT=1883
MQTT_USER=
MQTT_PASSWORD=
MQTT_TOPIC=gree
MQTT_QOS=0
MQTT_RETAIN=false
MQTT_KEEP_ALIVE=60

# Optional — Polling & Performance
UPDATE_INTERVAL=3                  # Normal polling interval (seconds)
ADAPTIVE_POLLING_TIMEOUT=45        # Adaptive polling duration (seconds)
ADAPTIVE_FAST_INTERVAL=0.8         # Fast polling interval (seconds)
EVENT_QUEUE_WORKERS=5              # Concurrent event workers
IMMEDIATE_RESPONSE_TIMEOUT=5       # Ultra-fast polling after commands (seconds)
```

### Tuning Tips

| Scenario | Recommendation |
|---|---|
| High traffic | Increase `EVENT_QUEUE_WORKERS` to 7–10 |
| Low latency | Decrease `ADAPTIVE_FAST_INTERVAL` to 0.5 |
| Resource constrained | Decrease `EVENT_QUEUE_WORKERS` to 3 |
| Battery powered | Increase `UPDATE_INTERVAL` to 5–10 |

## Usage

### MQTT Control

Set parameters:
```bash
gree/deviceId/set {"Pow":1,"SetTem":24}
```

Multiple devices simultaneously:
```bash
gree/device1/set {"Pow":1}
gree/device2/set {"SetTem":22}
gree/device3/set {"WdSpd":"auto"}
```

### Home Assistant

See the example configuration: [mqtt.yaml](https://github.com/monteship/GreeMQTT/blob/master/mqtt.yaml)

## Docker

### Build Locally

```bash
docker build -t greemqtt .
```

### Supported Architectures

- `linux/amd64` — x86_64
- `linux/arm64` — Raspberry Pi 4, Apple Silicon
- `linux/arm/v7` — Raspberry Pi 3

## Troubleshooting

- Ensure devices and the host are on the same network segment.
- Use `--network host` with Docker for device discovery.
- Check logs: `docker logs greemqtt`
- If auto-discovery fails (common on Docker Desktop, cloud VMs, NAS), specify IPs directly via `NETWORK`.

### Testing Device Connectivity

```bash
# Scan for Gree devices
echo '{"t":"scan"}' | socat - UDP-DATAGRAM:192.168.1.255:7000,broadcast

# Check if a device is reachable
nmap -sU -p 7000 192.168.1.41
```

### Docker UDP Issues

If discovery works on the host but not in Docker:
1. Verify `--network host` is set.
2. Open UDP port 7000: `sudo ufw allow 7000/udp`
3. Fall back to specifying IPs in `NETWORK` if broadcast is unsupported.

## Contributing

Contributions welcome! For major changes, please open an issue first.

## License

[MIT](LICENSE)
