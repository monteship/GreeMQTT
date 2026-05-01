# GreeMQTT

Bridge Gree air conditioners to MQTT for integration with Home Assistant and other smart home platforms. Discovers devices automatically, retrieves parameters, and enables control via MQTT topics.

**Single-container, event-driven architecture** — no Redis, RabbitMQ, or docker-compose required.

## Features

- Automatic device discovery via subnet broadcast or specific IPs
- **Periodic rediscovery** — devices that come online later are picked up automatically
- **Home Assistant MQTT Auto-Discovery** — climate entity + binary sensors appear without manual config
- MQTT-based control for setting and retrieving device parameters
- Fixed-interval polling with exponential error backoff (up to 60 s)
- Keep-alive state publish every 60 s even when parameters are unchanged
- Immediate state publish after parameter changes
- **Configurable tracking params** via `TRACKING_PARAMS` env var
- **Configurable log level** via `LOG_LEVEL` env var
- Configuration via environment variables or `.env` file
- Runs as non-root user inside Docker
- Multi-platform Docker support (amd64, arm64)

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

`pip install -e .` installs runtime dependencies only. Development tools (`ruff`, `ty`) are in the `dev` dependency group.

## Configuration

Create a `.env` file:

```env
# Required
MQTT_BROKER=192.168.1.50

# Optional — Network
# CIDR subnet for broadcast discovery or comma-separated IPs
NETWORK=192.168.1.0/24

# Optional — MQTT
MQTT_PORT=1883
MQTT_USER=
MQTT_PASSWORD=
MQTT_TOPIC=gree
MQTT_QOS=0
MQTT_RETAIN=false
MQTT_KEEP_ALIVE=60

# Optional — Polling & Performance
UPDATE_INTERVAL=3              # Polling interval in seconds

# Optional — Tracked Parameters
# Comma-separated list of device params to poll and publish.
# Defaults to all standard params when left empty.
TRACKING_PARAMS=

# Optional — Logging
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
```

### Default Tracked Parameters

When `TRACKING_PARAMS` is not set the following parameters are tracked:

```
Pow, Mod, SetTem, TemUn, WdSpd, Air, Blo, Health, SwhSlp, Lig,
SwingLfRig, SwUpDn, Quiet, Tur, StHt, HeatCoolType, TemRec, SvSt, TemSen
```

### Tuning Tips

| Scenario | Recommendation |
|---|---|
| Low latency | Decrease `UPDATE_INTERVAL` to 1–2 |
| Resource constrained | Increase `UPDATE_INTERVAL` to 5–10 |
| Track fewer params | Set `TRACKING_PARAMS` to only the params you need |

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

Devices are **automatically discovered** via MQTT Discovery — no manual YAML configuration needed.

The following entities are created for each device:

| Entity type | Name | Parameter |
|---|---|---|
| Climate | *(device name)* | Pow, Mod, SetTem, WdSpd, SwUpDn, TemSen |
| Binary sensor | Turbo | Tur |
| Binary sensor | Quiet Mode | Quiet |
| Binary sensor | Health Mode | Health |
| Binary sensor | Display Light | Lig |
| Binary sensor | Sleep Mode | SwhSlp |

For manual configuration, see: [mqtt.yaml](https://github.com/monteship/GreeMQTT/blob/master/mqtt.yaml)

## Docker

### Build Locally

```bash
docker build -t greemqtt .
```

The image is built with [uv](https://github.com/astral-sh/uv) and runs the application as a non-root user.

### Supported Architectures

- `linux/amd64` — x86_64
- `linux/arm64` — Raspberry Pi 4, Apple Silicon

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

### Development Setup

```bash
uv sync --group dev
uv run ruff check .
uv run ty
```

This project keeps lint/type tooling in the `dev` dependency group so production installs stay minimal.

## License

[MIT](LICENSE)
