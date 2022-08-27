[![PyPI version](https://badge.fury.io/py/ps2mqtt.svg)](https://badge.fury.io/py/ps2mqtt)

# ps2mqtt
Python daemon that gets information from [psutil](https://github.com/giampaolo/psutil) to an mqtt broker for integration with [Home Assistant](https://www.home-assistant.io).

## Install

You can install ps2mqtt from pypi:
```bash
$ pip install ps2mqtt
```

If you wish to run ps2mqtt through systemd, download the ps2mqtt.service file from this repository and edit according to your system.

Then just copy to systemd path and enable the service before starting:

```bash

$ sudo cp ps2mqtt.service /etc/systemd/system/

$ sudo systemctl enable ps2mqtt.service 

$ systemctl start ps2mqtt.service 

```

## Options

ps2mqtt has several command line options you should use when customizing ps2mqtt.service:

```txt
  -h, --help                                  show this help message and exit
  --config CONFIG                             configuration file, will be created if non existing
  --period PERIOD                             updates period in seconds
  --mqtt-server MQTT_SERVER                   MQTT server
  --mqtt-port MQTT_PORT                       MQTT port
  --mqtt-username MQTT_USERNAME               MQTT username
  --mqtt-password MQTT_PASSWORD               MQTT password
  --mqtt-base-topic MQTT_BASE_TOPIC           MQTT base topic
  --ha-discover-prefix HA_DISCOVER_PREFIX     HA discover mqtt prefix
  --ha-status-topic HA_STATUS_TOPIC           HA status mqtt topic
  ```
  
You can also store all the options in a file, just run all your options plus the `--config /etc/ps2mqtt.yaml` to store all your parameters in a config file. Next time you run, just use `--config /etc/ps2mqtt.yaml`.

## Docker

```
docker run -d \
  --name=ps2mqtt \
  -e MQTT_HOST=mqtt-broker-ip \
  -e MQTT_PORT=1883 \
  -e MQTT_USERNAME=username \
  -e MQTT_PASSWORD=password \
  -e MQTT_BASE_TOPIC=ps2mqtt \
  -e HA_DISCOVER_PREFIX=homeassistant \
  -e HA_STATUS_TOPIC=ps2mqtt/status \
  -e PERIOD=60 \
  --restart unless-stopped \
  sthopeless/ps2mqtt:latest
```

Or copy the docker-compose.yml file edit with your configurations and start with `docker-compose up -d` or paste into Portainer stacks and run.
