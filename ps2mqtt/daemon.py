#!/usr/bin/env python3
"""Host Statistic Information to MQTT."""

import argparse
import json
import logging
import platform
import os
import sched
import time
from datetime import datetime
from decimal import Decimal, getcontext

import paho.mqtt.client as mqtt
import psutil
import yaml
from slugify import slugify
from yaml import Dumper

from . import __version__
getcontext().prec = 2

MQTT_BASE_TOPIC = f"ps2mqtt/{slugify(platform.node())}"
MQTT_PS2MQTT_STATUS = "{}/status"
MQTT_STATE_TOPIC = "{}/{}"
MQTT_AVAILABLE = "online"
MQTT_NOT_AVAILABLE = "offline"
HA_DISCOVERY_PREFIX = "{}/sensor/ps2mqtt_{}/{}/config"

OPTIONAL_ATTR = ["device_class", "icon", "unit_of_measurement"]

log_format = "%(asctime)s %(levelname)s: %(message)s"
logging.basicConfig(format=log_format, level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger(__name__)

last = {}


def rate(key, value):
    """Calculate running rates."""
    rate = 0
    now = time.time()
    if key in last:
        ltime, lvalue = last[key]
        rate = Decimal(value - lvalue) / Decimal(now - ltime)
    last[key] = now, value

    return float(rate)


def load_properties(config):
    """Define which properties to publish."""
    properties = {
        "cpu_percent": {
            "unit_of_measurement": "%",
            "icon": "mdi:chip",
            "call": lambda: psutil.cpu_percent(interval=None),
        },
        "virtual_memory": {
            "unit_of_measurement": "%",
            "icon": "mdi:memory",
            "call": lambda: psutil.virtual_memory().percent,
        },
        "uptime": {
            "device_class": "timestamp",
            "call": lambda: datetime.fromtimestamp(psutil.boot_time())
            .astimezone()
            .isoformat(),
        },
        "bytes_sent": {
            "unit_of_measurement": "MiB",
            "icon": "mdi:upload-network",
            "call": lambda: int(psutil.net_io_counters().bytes_sent / 1000000),
        },
        "bytes_recv": {
            "unit_of_measurement": "MiB",
            "icon": "mdi:download-network",
            "call": lambda: int(psutil.net_io_counters().bytes_recv / 1000000),
        },
        "upload": {
            "unit_of_measurement": "kbps",
            "icon": "mdi:upload-network",
            "call": lambda: rate("upload", psutil.net_io_counters().bytes_sent / 1000),
        },
        "download": {
            "unit_of_measurement": "kbps",
            "icon": "mdi:download-network",
            "call": lambda: rate(
                "download", psutil.net_io_counters().bytes_recv / 1000
            ),
        },
    }

    storage_path_list = config["storage_paths"].split(",")

    for path in storage_path_list:
        disk_name = "root" if path == "/" else slugify(path)
        properties[f"{disk_name}_disk_usage"] = {
            "unit_of_measurement": "%",
            "icon": "mdi:harddisk",
            "call": lambda: psutil.disk_usage(path).percent,
        }

    if hasattr(psutil, "sensors_temperatures"):
        for temp_sensor in psutil.sensors_temperatures():
            properties[temp_sensor] = {
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "call": lambda: psutil.sensors_temperatures()[temp_sensor][0].current,
            }

    return properties


def gen_ha_config(sensor, properties, base_topic):
    """Generate Home Assistant Configuration."""
    json_config = {
        "name": sensor,
        "unique_id": slugify(f"{platform.node()} {sensor}"),
        "object_id": slugify(f"{platform.node()} {sensor}"),
        "state_topic": MQTT_STATE_TOPIC.format(base_topic, sensor),
        "availability_topic": MQTT_PS2MQTT_STATUS.format(base_topic),
        "payload_available": MQTT_AVAILABLE,
        "payload_not_available": MQTT_NOT_AVAILABLE,
        "device": {
            "identifiers": f"{platform.node()}_ps2mqtt",
            "name": f"{platform.node()}",
            "sw_version": platform.platform(),
            "model": platform.system(),
            "manufacturer": f"ps2mqtt {__version__}",
        },
    }
    for attr in OPTIONAL_ATTR:
        if attr in properties[sensor]:
            json_config[attr] = properties[sensor][attr]

    return json.dumps(json_config)


def status(mqttc, properties, status_scheduler, period, base_topic):
    """Publish status and schedule the next."""
    for p in properties.keys():
        try:
            mqttc.publish(
                MQTT_STATE_TOPIC.format(base_topic, p), properties[p]["call"]()
            )
        except Exception as e:
            logger.error(e)
    status_scheduler.enter(
        period, 1, status, (mqttc, properties, status_scheduler, period, base_topic)
    )

    mqttc.publish(
        MQTT_PS2MQTT_STATUS.format(base_topic),
        MQTT_AVAILABLE,
    )


def publish_ha_discovery(client, properties, config):
    """Publish HA discovery information."""

    client.publish(
        MQTT_PS2MQTT_STATUS.format(config["mqtt_base_topic"]),
        MQTT_AVAILABLE,
        retain=False,
    )
    for p in properties.keys():
        logger.debug("HA Discovery configuration for %s", p)
        client.publish(
            HA_DISCOVERY_PREFIX.format(
                config["ha_discover_prefix"], slugify(platform.node()), p
            ),
            gen_ha_config(p, properties, config["mqtt_base_topic"]),
            retain=True,
        )


def on_message(client, userdata, _flags):
    """MQTT Message callback."""
    publish_ha_discovery(client, *userdata)


def on_connect(client, userdata, _flags, _result):
    """MQTT Connect callback."""

    _, config = userdata
    client.subscribe(config["ha_status_topic"])
    publish_ha_discovery(client, *userdata)


def main():

    """Start main daemon."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", help="configuration file, will be created if non existing"
    )
    parser.add_argument(
        "--period", help="updates period in seconds", type=int, default=os.environ.get("PERIOD", 60)
    )
    parser.add_argument("--mqtt-server", help="MQTT server", default=os.environ.get("MQTT_SERVER", "localhost"))
    parser.add_argument("--mqtt-port", help="MQTT port", type=int, default=os.environ.get("MQTT_PORT", 1883))
    parser.add_argument("--mqtt-username", help="MQTT username", default=os.environ.get("MQTT_USERNAME", None))
    parser.add_argument("--mqtt-password", help="MQTT password", default=os.environ.get("MQTT_PASSWORD", None))
    parser.add_argument(
        "--mqtt-base-topic", help="MQTT base topic", default=os.environ.get("MQTT_BASE_TOPIC", MQTT_BASE_TOPIC)
    )
    parser.add_argument(
        "--ha-discover-prefix", help="HA discover mqtt prefix", default=os.environ.get("HA_DISCOVER_PREFIX", "homeassistant")
    )
    parser.add_argument(
        "--ha-status-topic", help="HA status mqtt topic", default=os.environ.get("HA_STATUS_TOPIC", "homeassistant/status")
    )
    parser.add_argument(
        '--storage-paths', help="Path(s) for storage usage monitoring (comma separated values)", default=os.environ.get("STORAGE_PATHS", "/")
    )
    args = parser.parse_args()

    config_file = {}

    try:
        if args.config:
            with open(args.config, "r") as infile:
                logger.debug("Loading configuration from <%s>", args.config)
                config_file = yaml.safe_load(infile)
    except FileNotFoundError:
        logger.info(
            "Configuration file %s not found. Using default values", args.config
        )
    finally:

        config = {
            "mqtt_server": config_file.get("mqtt_server", args.mqtt_server),
            "mqtt_port": config_file.get("mqtt_port", args.mqtt_port),
            "mqtt_username": config_file.get("mqtt_username", args.mqtt_username),
            "mqtt_password": config_file.get("mqtt_password", args.mqtt_password),
            "mqtt_base_topic": config_file.get("mqtt_base_topic", args.mqtt_base_topic),
            "ha_discover_prefix": config_file.get(
                "ha_discover_prefix", args.ha_discover_prefix
            ),
            "ha_status_topic": config_file.get("ha_status_topic", args.ha_status_topic),
            "period": config_file.get("period", args.period),
            "storage_paths": config_file.get("storage_paths", args.storage_paths)
        }

        for key in list(config):
            if args.__dict__[key] != parser.get_default(
                key
            ):  # update config_file from args if not default
                logger.debug("Updating %s with %s", key, args.__dict__[key])
                config[key] = args.__dict__[key]
            if config[key] is None:  # remove keys which are None
                del config[key]

        if args.config:
            with open(args.config, "w", encoding="utf8") as outfile:
                yaml.dump(
                    config,
                    outfile,
                    default_flow_style=False,
                    allow_unicode=True,
                    Dumper=Dumper,
                )
                logger.info("Saving configuration in %s", args.config)

    properties = load_properties(config)

    logger.debug("Connecting to %s:%s", config["mqtt_server"], config["mqtt_port"])
    mqttc = mqtt.Client(
        client_id=slugify(f"ps2mqtt {platform.node()}"),
        userdata=(properties, config),
    )
    mqttc.will_set(
        MQTT_PS2MQTT_STATUS.format(config["mqtt_base_topic"]),
        MQTT_NOT_AVAILABLE,
        retain=True,
    )
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect

    if "mqtt_username" in config and "mqtt_password" in config:
        mqttc.username_pw_set(config["mqtt_username"], config["mqtt_password"])

    try:
        mqttc.connect(config["mqtt_server"], config["mqtt_port"], 60)
        mqttc.loop_start()

        status_scheduler = sched.scheduler(time.time, time.sleep)
        status(
            mqttc,
            properties,
            status_scheduler,
            config["period"],
            config["mqtt_base_topic"],
        )

        status_scheduler.run()  # block indefinitely

    except Exception as e:
        logger.error(
            "While connecting to %s:%s %s",
            config["mqtt_server"],
            config["mqtt_port"],
            e,
        )


if __name__ == "__main__":
    main()
