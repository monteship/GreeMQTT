# Project: GreeMQTT

## Description
GreeMQTT bridges Gree air conditioners and similar devices to MQTT, enabling seamless integration with smart home platforms like Home Assistant. It discovers Gree devices on your network, retrieves their parameters, and allows control via MQTT topics.

## Features
- Automatic device discovery on the local network
- Periodic device parameter updates
- MQTT-based control for setting and retrieving device parameters
- Configuration via environment variables or `.env` file
- Docker support for easy deployment

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
UPDATE_INTERVAL=5
```
## Configuration Explanation
- `NETWORK`: Comma-separated list of Gree device IPs or leave empty for auto-discovery.
- `MQTT_BROKER`: Address of your MQTT broker.
- `MQTT_PORT`: MQTT broker port (default: 1883).
- `MQTT_USER`/`MQTT_PASSWORD`: MQTT credentials.
- `MQTT_TOPIC`: Base topic for publishing and subscribing.
- `UPDATE_INTERVAL`: Polling interval in seconds.
- `SUBNET`: (Optional) subnet for device discovery (default: `192.168.1.0/24`).
- `UDP_PORT`: (Optional) UDP port for device communication (default: `7000`).

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

### 2. MQTT Control
Control devices by publishing messages to the specified MQTT topic. The application listens for incoming messages and updates device parameters accordingly.

### 3. Parameter Updates
The application periodically retrieves and publishes device parameters to the specified MQTT topic. The update interval is configurable.

### 4. Example MQTT Messages
- To set a parameter:
```bash
MQTT_TOPIC/deviceId/set {"Pow":1,"SetTem":24}
```

## Automatic Device Discovery
If the `NETWORK` environment variable is not set, GreeMQTT will automatically scan your local network for compatible Gree devices on port 7000. This makes setup easier, as you do not need to manually specify device IP addresses. The discovered devices will be added to the internal database and managed automatically.

### Home Assistant Integration
Add the following to your Home Assistant `configuration.yaml` to subscribe to GreeMQTT topics:
```yaml
- unique_id: "kitchen_ac"
  name: "Kitchen Gree AC"
  precision: 1
  temperature_command_topic: "gree/deviceId/set"
  temperature_command_template: >
    {"SetTem":{{ value | int }}}
  temperature_state_topic: "gree/deviceId"
  temperature_state_template: "{{ value_json.SetTem }}"

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
    {"WdSpd":"{{ value }}"}
  fan_mode_state_topic: "gree/deviceId"
  fan_mode_state_template: "{{ value_json.WdSpd }}"
  fan_modes:
    - auto
    - low
    - medium
    - high

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
  retain: false
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
