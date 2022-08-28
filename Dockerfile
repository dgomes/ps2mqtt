FROM python:3-buster

LABEL maintainer="sthopeless <hopelessautomations@gmail.com>"

ENV MQTT_HOST="localhost"
ENV MQTT_PORT="1883"
ENV MQTT_USERNAME="username"
ENV MQTT_PASSWORD="password"
ENV MQTT_BASE_TOPIC="ps2mqtt"
ENV HA_DISCOVER_PREFIX="homeassistant"
ENV HA_STATUS_TOPIC="ps2mqtt/status"
ENV PERIOD="60"

RUN pip install --upgrade pip && pip install ps2mqtt

CMD ["sh", "-c", "ps2mqtt --period ${PERIOD} --mqtt-server ${MQTT_HOST} --mqtt-port ${MQTT_PORT} --mqtt-username ${MQTT_USERNAME} --mqtt-password ${MQTT_PASSWORD} --mqtt-base-topic ${MQTT_BASE_TOPIC} --ha-discover-prefix ${HA_DISCOVER_PREFIX} --ha-status-topic ${HA_STATUS_TOPIC}"]
