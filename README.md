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
pip install -r requirements.txt
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
python main.py
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
## Logging
The application uses the `logging` module to log messages. You can configure the logging level in the `.env` file or as an environment variable.
```env
LOG_LEVEL=DEBUG
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
