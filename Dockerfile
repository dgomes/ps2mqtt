FROM python:3-buster

LABEL maintainer="sthopeless <hopelessautomations@gmail.com>"

RUN pip install --upgrade pip && pip install ps2mqtt

CMD ["sh", "-c", "ps2mqtt"]
