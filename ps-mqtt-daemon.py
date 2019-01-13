#!/usr/bin/env python3
__author__ = "Diogo Gomes"
__version__ = "0.0.1"
__email__ = "diogogomes@gmail.com"

import argparse
import logging
import yaml
import json
import io
import re

import paho.mqtt.client as mqtt

import platform
import psutil
import sched, time

DEFAULT_MQTT_BASE_TOPIC = "ps2mqtt"
DEFAULT_HA_DISCOVERY_PREFIX = "homeassistant_fake"

MQTT_BASE_TOPIC = DEFAULT_MQTT_BASE_TOPIC+"/"+platform.node()
MQTT_PS2MQTT_STATUS = "{}/status"
MQTT_STATE_TOPIC = "{}/{}"
MQTT_AVAILABLE = "online"
MQTT_NOT_AVAILABLE = "offline"

HA_DISCOVERY_PREFIX="{}/sensor/ps2mqtt_"+platform.node()+"/{}/config"

def load_properties():
    properties = {"cpu_percent": {"unit": "%", "icon": "mdi:chip", "call": lambda: psutil.cpu_percent(interval=None)},
                  "virtual_memory": {"unit": "%", "icon": "mdi:memory", "call": lambda: psutil.virtual_memory().percent},
                  "bytes_sent": {"unit": "MiB", "icon": "mdi:upload-network", "call": lambda: psutil.net_io_counters().bytes_sent/1000000},
                  "bytes_recv": {"unit": "MiB", "icon": "mdi:download-network", "call": lambda: psutil.net_io_counters().bytes_recv/1000000},
                }

    for temp_sensor in psutil.sensors_temperatures():
        properties[temp_sensor] = {"unit": "°C", "icon": "mdi:thermometer", "call": lambda: psutil.sensors_temperatures()[temp_sensor][0].current}

    return properties

def gen_ha_config(sensor, properties):
    hostname = platform.node()
    json_config = {
        "name": "{} {}".format(hostname, sensor),
        "unique_id": "{}_{}".format(hostname, sensor),
        "state_topic": MQTT_STATE_TOPIC.format(MQTT_BASE_TOPIC, sensor),
        "availability_topic": MQTT_PS2MQTT_STATUS.format(MQTT_BASE_TOPIC),
        "payload_available": MQTT_AVAILABLE,
        "payload_not_available": MQTT_NOT_AVAILABLE,
        "unit_of_measurement": properties[sensor]['unit'],
        "icon": properties[sensor]['icon'],
    }
    return json.dumps(json_config)

log_format = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(__name__)

def status(mqttc, properties, s, period):
    for p in properties.keys():
        mqttc.publish(MQTT_STATE_TOPIC.format(MQTT_BASE_TOPIC, p), properties[p]["call"]())
    s.enter(period, 1, status, (mqttc, properties, s, period))

def on_connect(client, properties, flags, result, ha_prefix=DEFAULT_HA_DISCOVERY_PREFIX):
    client.publish(MQTT_PS2MQTT_STATUS.format(MQTT_BASE_TOPIC),MQTT_AVAILABLE,retain=True)
    for p in properties.keys():
        logger.debug("Adding %s", p)
        rc = client.publish(HA_DISCOVERY_PREFIX.format(ha_prefix, p), gen_ha_config(p, properties), retain=True)

def main_loop(period, mqtt_server, mqtt_port, ha_prefix):
    properties = load_properties()

    logger.debug("Connecting to %s:%s", mqtt_server, mqtt_port)
    mqttc = mqtt.Client(client_id="ps2mqtt_"+platform.node(), userdata=properties)
    mqttc.will_set(MQTT_PS2MQTT_STATUS.format(MQTT_BASE_TOPIC),MQTT_NOT_AVAILABLE,retain=True)
    mqttc.on_connect = lambda a,b,c,d: on_connect(a,b,c,d, ha_prefix)

    mqttc.connect(mqtt_server, mqtt_port, 60)

    mqttc.loop_start()

    s = sched.scheduler(time.time, time.sleep)
    status(mqttc, properties, s, period)

    s.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="configuration file", default="config.ini")
    parser.add_argument("--period", help="updates period in seconds", type=int, default=60)
    parser.add_argument("--mqtt-server", help="MQTT server", default="localhost")
    parser.add_argument("--mqtt-port", help="MQTT port", type=int, default=1883)
    parser.add_argument("--mqtt-base-topic", help="MQTT base topic", default=DEFAULT_MQTT_BASE_TOPIC)
    parser.add_argument("--ha-discover-prefix", help="HA discover mqtt prefix", default="homeassistant")

    args = parser.parse_args()

    config = {"mqtt_server": args.mqtt_server,
              "mqtt_port": args.mqtt_port,
              "mqtt_base_topic": args.mqtt_base_topic,
              "ha_discover_prefix": args.ha_discover_prefix,
              }

    try:
        with open(args.config, 'r') as stream:
            logger.debug("Loading configuration from <%s>", args.config)
            config = yaml.load(stream)

        MQTT_BASE_TOPIC = config["mqtt_base_topic"]

        main_loop(config["period"], config["mqtt_server"], config["mqtt_port"], config["ha_discover_prefix"])
    except FileNotFoundError as e:
        logger.info("Configuration file %s created, please reload daemon", args.config)
    except KeyError as e:
        missing_key = e.args[0]
        config[missing_key] = args.__dict__[missing_key]
        logger.info("Configuration file updated, please reload daemon")
    finally:
        with io.open(args.config, 'w', encoding="utf8") as outfile:
            yaml.dump(config, outfile, default_flow_style=False, allow_unicode=True)

