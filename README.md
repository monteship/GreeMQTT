# Project: GreeMQTT

## Description
This project integrates Gree devices with MQTT, enabling communication and control via MQTT topics. It discovers devices on the network, retrieves their parameters, and allows parameter updates through MQTT.

## Features
- Device discovery on the network.
- Periodic parameter updates from devices.
- MQTT-based control for setting and retrieving device parameters.
- Configurable via environment variables.

## Requirements
- Python 3.8+
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
docker run -it \
  --network="host" \
  -e MQTT_BROKER='your_mqtt_broker' \
  -e MQTT_PORT='your_mqtt_port' \
  -e MQTT_USER='your_mqtt_user' \
  -e MQTT_PASSWORD='your_mqtt_password' \
  -e MQTT_TOPIC='your_mqtt_topic' \
  -e NETWORK='device_ip1,device_ip2' \ 
  -e UPDATE_INTERVAL=5 \
  --name greemqtt \
  monteship/greemqtt:latest
```

## Usage
### 1. Device Discovery
The application will automatically discover devices on the specified network. You can specify the network in the `.env` file or as an environment variable.
### 2. MQTT Control
You can control the devices by publishing messages to the specified MQTT topic. The application will listen for incoming messages and update the device parameters accordingly.
### 3. Parameter Updates
The application will periodically retrieve and publish device parameters to the specified MQTT topic. You can configure the update interval in the `.env` file or as an environment variable.
### 4. Example MQTT Messages
- To set a parameter:
```bash
MQTT_TOPIC/deviceId/set {"Pow":1,"SetTem":24}
```
## Home Assistant Integration
To integrate with Home Assistant, you can use the MQTT integration. Add the following configuration to your `configuration.yaml` file:
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
- Ensure that the devices are on the same network as the application.
- Check the MQTT broker settings and ensure that the application can connect to it.
- Check the logs for any error messages.
- If you encounter any issues, please open an issue on the GitHub repository.

## Contributing
Contributions are welcome! If you have suggestions for improvements or new features, please open an issue or submit a pull request.
## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
