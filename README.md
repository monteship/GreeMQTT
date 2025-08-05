# GreeMQTT

## Description
GreeMQTT bridges Gree air conditioners and similar devices to MQTT, enabling integration with smart home platforms like Home Assistant. It discovers Gree devices on your network, retrieves their parameters, and allows control via MQTT topics with fast response times and adaptive polling.

## Key Features
- **Fast Response System**: Low-latency MQTT message processing with direct callbacks
- **Improved Responsiveness**: Sub-second command response times (typically 50-150ms)
- **Direct Execution**: Commands processed without queue delays
- **Concurrent Processing**: Multiple MQTT commands processed simultaneously  
- **Immediate Feedback**: Device state publishing after parameter changes
- **Performance Monitoring**: Processing metrics and callback statistics
- **Adaptive Polling**: Automatically adjusts polling frequency based on activity
- **Low Latency**: Callback architecture reduces processing bottlenecks
- Automatic device discovery on the local network
- Periodic device parameter updates with configurable intervals
- MQTT-based control for setting and retrieving device parameters
- Configuration via environment variables or `.env` file
- Docker support for easy deployment

## Fast Response System

### Low-Latency Architecture
GreeMQTT features a callback system that reduces traditional queue bottlenecks:

- **Direct Message Routing**: MQTT messages trigger callbacks upon arrival
- **Reduced Queue Processing**: Minimizes worker queues and message delays
- **Concurrent Execution**: Multiple callbacks execute simultaneously for different devices
- **Quick State Updates**: Device states published promptly after parameter changes

### Performance Improvements
**Previous Implementation**:
- Message → Queue → Worker → Processing → Response
- Response time: 200-1000ms
- Single-threaded message handling

**Current Implementation**:
- Message → Direct Callback → Processing → Response
- Response time: 50-150ms (improved performance)
- Concurrent processing for multiple devices

## Adaptive Polling Features

### Multi-Tier Polling System
Combined with the callback system for improved responsiveness:

- **High-Frequency Mode (0.1s)**: Fast polling for 3 seconds after a command
- **Medium-Frequency Mode (0.3s)**: Elevated polling for the next 12 seconds  
- **Fast Mode (0.8s)**: Accelerated polling for remaining adaptive time
- **Normal Mode (3s)**: Standard polling when devices are idle

### Message Processing
- **Direct callback registration** for each device topic
- **Reduced-latency message execution** without queuing delays
- **Concurrent callback processing** for multiple simultaneous commands
- **Processing time tracking** with callback execution metrics

### Performance Monitoring
- Response count tracking
- Callback execution statistics
- Processing time tracking
- Average performance metrics
- Command frequency monitoring per device
- Adaptive polling statistics

## Requirements
- Python 3.12+
- Docker (optional, for containerized deployment)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/monteship/GreeMQTT.git
cd GreeMQTT
```

### 2. Install Dependencies
```bash
python -m pip install -e .
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory and set the following variables:
```env
NETWORK=192.168.1.100,192.168.1.101 
MQTT_BROKER=your_mqtt_broker
MQTT_PORT=your_mqtt_port
MQTT_USER=your_mqtt_user
MQTT_PASSWORD=your_mqtt_password
MQTT_TOPIC=your_mqtt_topic
UPDATE_INTERVAL=3
ADAPTIVE_POLLING_TIMEOUT=45
ADAPTIVE_FAST_INTERVAL=0.8
MQTT_MESSAGE_WORKERS=3
IMMEDIATE_RESPONSE_TIMEOUT=5
```

## Configuration Explanation

### Basic Configuration
- `NETWORK`: Comma-separated list of Gree device IPs or leave empty for auto-discovery.
- `MQTT_BROKER`: Address of your MQTT broker.
- `MQTT_PORT`: MQTT broker port (default: 1883).
- `MQTT_USER`/`MQTT_PASSWORD`: MQTT credentials.
- `MQTT_TOPIC`: Base topic for publishing and subscribing.
- `SUBNET`: (Optional) subnet for device discovery (default: `192.168.1.0/24`).
- `UDP_PORT`: (Optional) UDP port for device communication (default: `7000`).

### Enhanced Responsiveness Configuration
- `UPDATE_INTERVAL`: Normal polling interval in seconds (default: 3, reduced from 4 for better responsiveness).
- `ADAPTIVE_POLLING_TIMEOUT`: Duration of adaptive polling in seconds (default: 45, optimized for faster return to normal).
- `ADAPTIVE_FAST_INTERVAL`: Fast polling interval during adaptive mode (default: 0.8, improved from 1 second).
- `MQTT_MESSAGE_WORKERS`: Number of concurrent message processor workers (default: 3).
- `IMMEDIATE_RESPONSE_TIMEOUT`: Duration of ultra-fast polling after commands (default: 5 seconds).

### Performance Tuning Tips
- **High-traffic environments**: Increase `MQTT_MESSAGE_WORKERS` to 5-7
- **Low-latency requirements**: Decrease `ADAPTIVE_FAST_INTERVAL` to 0.5
- **Battery-powered setups**: Increase `UPDATE_INTERVAL` to 5-10 seconds
- **Critical applications**: Decrease `IMMEDIATE_RESPONSE_TIMEOUT` for longer ultra-fast periods

### 4. Run the Application
```bash
python -m GreeMQTT
```

## Docker Deployment
### 1. Build the Docker Image
```bash
docker build -t greemqtt .
```

### 2. Run the Docker Container
```bash
docker run --env-file .env --network host --name greemqtt monteship/greemqtt:latest
```
- `--env-file .env`: Loads environment variables from your `.env` file.
- `--network host`: Required for device discovery on your local network.

### 3. Health Monitoring
The Docker image includes a built-in health check that monitors:
- Application responsiveness
- Required environment variables
- MQTT broker connectivity

Docker will automatically check the container health every 30 seconds. You can view health status with:
```bash
docker ps
docker inspect greemqtt --format='{{.State.Health.Status}}'
```

The health check logs can be viewed with:
```bash
docker logs greemqtt
```

## Usage

### 1. Device Discovery
The application will automatically discover devices on the specified network. You can specify the network in the `.env` file or as an environment variable.

### 2. MQTT Control with Enhanced Responsiveness
Control devices by publishing messages to the specified MQTT topic. The application now provides:
- **Sub-second response times** for immediate feedback
- **Concurrent command processing** for multiple simultaneous operations
- **Automatic state publishing** after each parameter change

### 3. Intelligent Parameter Updates
The application uses smart polling that automatically adjusts based on activity:
- **0.1-second updates** immediately after commands for instant feedback
- **Gradual transition** to normal polling as activity decreases
- **Efficient resource usage** during idle periods

### 4. Example MQTT Messages with Fast Response
- To set a parameter (now with sub-second feedback):
```bash
MQTT_TOPIC/deviceId/set {"Pow":1,"SetTem":24}
# Response typically received within 100-300ms
```

- Multiple concurrent commands are now supported:
```bash
# These commands can be processed simultaneously
MQTT_TOPIC/device1/set {"Pow":1}
MQTT_TOPIC/device2/set {"SetTem":22}
MQTT_TOPIC/device3/set {"WdSpd":"auto"}
```

### 5. Performance Monitoring
Monitor system performance through logs:
```bash
# Processing time logs show responsiveness metrics
[DEBUG] Set parameters for device - processing_time_ms: 150.5, avg_processing_time_ms: 200.2
```

## Automatic Device Discovery
If the `NETWORK` environment variable is not set, GreeMQTT will automatically scan your local network for compatible Gree devices on port 7000. This makes setup easier, as you do not need to manually specify device IP addresses. The discovered devices will be added to the internal database and managed automatically.

### Home Assistant Integration
Add the following to your Home Assistant `configuration.yaml` to subscribe to GreeMQTT topics:
```yaml
- unique_id: "livingroom_ac"
  name: "Living Room Gree AC"
  precision: 1
  temperature_command_topic: "gree/deviceId/set"
  temperature_command_template: >
    {"SetTem":{{ value | int }}}
  temperature_state_topic: "gree/deviceId"
  temperature_state_template: "{{ value_json.SetTem }}"
  max_temp: 30

  current_temperature_topic: "gree/deviceId"
  current_temperature_template: "{{ value_json.TemSen }}"

  mode_command_topic: "gree/deviceId/set"
  mode_command_template: >
    {% if value == 'off' %}
      {"Pow":"off"}
    {% else %}
      {"Pow":"on","Mod":"{{ value }}"}
    {% endif %}
  mode_state_topic: "gree/deviceId"
  mode_state_template: >
    {% if value_json.Pow == "off" %}
      off
    {% else %}
      {{ value_json.Mod }}
    {% endif %}
  modes:
    - "off"
    - "auto"
    - "cool"
    - "dry"
    - "fan_only"
    - "heat"

  fan_mode_command_topic: "gree/deviceId/set"
  fan_mode_command_template: >
    {% if value == 'turbo' %}
      {"Tur":"on", "Quiet":"off"}
    {% elif value == 'quiet' %}
      {"Quiet":"on", "Tur":"off"}
    {% else %}
      {"WdSpd":"{{ value }}", "Tur":"off", "Quiet":"off"}
    {% endif %}
  fan_mode_state_topic: "gree/deviceId"
  fan_mode_state_template: >
    {% if value_json.Tur == "on" %}
      turbo
    {% elif value_json.Quiet == "on" %}
      quiet
    {% else %}
      {{ value_json.WdSpd }}
    {% endif %}
  fan_modes:
    - auto
    - low
    - medium-low
    - medium
    - medium-high
    - high
    - turbo
    - quiet
  swing_mode_command_topic: "gree/deviceId/set"
  swing_mode_command_template: >
    {"SwUpDn":"{{ value }}"}
  swing_mode_state_topic: "gree/deviceId"
  swing_mode_state_template: "{{ value_json.SwUpDn }}"
  swing_modes:
    - "default"
    - "full_swing"
    - "fixed_upmost"
    - "fixed_middle_up"
    - "fixed_middle"
    - "fixed_middle_low"
    - "fixed_lowest"
    - "swing_downmost"
    - "swing_middle_low"
    - "swing_middle"
    - "swing_middle_up"
    - "swing_upmost"

  qos: 0
  retain: true
```

## Troubleshooting
- Ensure devices are on the same network as the application.
- Verify MQTT broker settings and connectivity.
- Check logs for error messages.
- For issues, open an issue on the GitHub repository.
- Ensure your devices and the host/container are on the same network segment.
- Use `--network host` with Docker for proper device discovery.
- Check logs for errors: `docker logs greemqtt` or console output.

### Docker Health Check Issues
If the Docker container shows as unhealthy, you can:
- Check health status: `docker inspect greemqtt --format='{{.State.Health.Status}}'`
- View health check logs in the container logs: `docker logs greemqtt`
- Manually run the health check: `docker exec greemqtt python /app/healthcheck.py`
- Verify MQTT broker connectivity from the container: `docker exec greemqtt nc -zv $MQTT_BROKER 1883`

### Docker UDP Broadcast Troubleshooting

If device discovery works on the host but not inside Docker:

- Ensure you run the container with `--network host` (required for UDP broadcast).
- Make sure UDP port 7000 is open on your host firewall:
  `sudo ufw allow 7000/udp`
- Some environments (cloud VMs, certain NAS, or Docker Desktop on Mac/Windows) do not support `--network host` or UDP broadcast. In these cases, device discovery may not work from inside Docker.
- As a workaround, specify device IPs directly in your `.env` file using the `NETWORK` variable:
  ```
  NETWORK=192.168.1.41,192.168.1.40
  ```
- You can test UDP broadcast from inside the container:
  ```bash
  docker exec -u root -it greemqtt bash
  apt update && apt install -y socat
  echo '{"t":"scan"}' | socat - UDP-DATAGRAM:192.168.1.255:7000,broadcast
  ```
  If you see no output, UDP broadcast is not working in your Docker environment.


## Helpful commands
```bash
echo '{"t":"scan"}' | socat - UDP-DATAGRAM:192.168.1.255:7000,broadcast
# This command sends a scan request to discover Gree devices on the local network.
# Example output:
# {"t":"pack","i":1,"uid":0,"cid":"502cc6a2bdb5","tcid":"","pack":"LP24Ek0OaYogxs3iQLjL4IJZ8Tc1GhwGgU1QWl/HwnMFDrdIfUg0NJmUJNu7AwXqwAOx/ClklKGq9spJo3oG4TnWMzaLQaaw1aFXlE9k71L0cMm8bsr/y4FkxumpRg1t0xV8+/m47OTBNaX/8aUl1dlSUvgTB047e91whA8Mx+BzMQoS41XpnORSG7+GfavhnKYbt0iIDsdp8/ftXlA9HkRwlDB/b65kWltUYwGtbty80gq9HxK8Loa8WXVjgZcP4Vf5MjKxa60Xt5J1oI+lsxUuXTHkgunLg76WWGy+euo="}
# {"t":"pack","i":1,"uid":0,"cid":"","tcid":"","pack":"LP24Ek0OaYogxs3iQLjL4EZ+Xq1EbShb2ys5VE0+JfaMa9lM2RqI/KytvJ32IsGSZXrOr+MakVzzXHbghPeyiui/giRwi/22P1NeJSbhyoDt21IYC5nmTB0FSNCtGSQCq+qmiRmaZjpRwuO7Fe5EbuQqhDgWpIlXPBd0kSiOb/EJPRFZzjLrUDkhvMjz32yVMkOVsFsTAafzePY7qSehbZIhsbG6Ck8X1+GBAEqEtdxSARmdHzsfl0hV7CQKMyULqf7+wHqDf2mz9uzNFv2ejeSQamdCPojzhBoiY0/QI0FjKzbWMRG6ftFbCalgfYcMphjtFkYpY2Dv1B44KKRYoOqBuo3ABqh7zjtQE21CWaSsH6bNGMeBkcgCC2vvIqV6"}%      
# Output indicates that Gree devices are present on the network, showing their unique identifiers and capabilities.


nmap -sU -p 7000 192.168.1.41
# This command scans the specified IP address for open UDP port 7000, which is used by Gree devices.
# Example output:
# Starting Nmap 7.97 ( https://nmap.org ) at 2025-06-22 17:43 +0300
# Nmap scan report for 192.168.1.41
# Host is up (0.023s latency).

# PORT     STATE         SERVICE
# 7000/udp open|filtered afs3-fileserver
# MAC Address: 50:2C:C6:A2:BD:B5 (Gree Electric Appliances, OF Zhuhai)

# Nmap done: 1 IP address (1 host up) scanned in 4.93 seconds
# Output indicates that the Gree device is reachable on port 7000, confirming its presence on the network.

```


## Contributing
Contributions are welcome! Please open an issue or submit a pull request for suggestions or improvements.
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## Support
For questions or issues, open an issue on [GitHub](https://github.com/monteship/GreeMQTT/issues).

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
