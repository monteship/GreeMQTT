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
docker run --env-file .env --network host --name greemqtt greemqtt
```
- `--env-file .env`: Loads environment variables from your `.env` file.
- `--network host`: Required for device discovery on your local network.

## Configuration Example

Example `.env` file:
```env
NETWORK=192.168.1.100,192.168.1.101
MQTT_BROKER=192.168.1.10
MQTT_PORT=1883
MQTT_USER=homeassistant
MQTT_PASSWORD=yourpassword
MQTT_TOPIC=gree
UPDATE_INTERVAL=5
```

- `NETWORK`: Comma-separated list of Gree device IPs or leave empty for auto-discovery.
- `MQTT_BROKER`: Address of your MQTT broker.
- `MQTT_PORT`: MQTT broker port (default: 1883).
- `MQTT_USER`/`MQTT_PASSWORD`: MQTT credentials.
- `MQTT_TOPIC`: Base topic for publishing and subscribing.
- `UPDATE_INTERVAL`: Polling interval in seconds.

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

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for suggestions or improvements.
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## Support
For questions or issues, open an issue on [GitHub](https://github.com/monteship/GreeMQTT/issues).

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
