# FROM python:3.11
FROM python:3.12-slim

WORKDIR /app

RUN apt update; apt install -y pulseaudio libportaudio2 alsa-utils sox libsox-fmt-all espeak-ng cmake nano

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

ENTRYPOINT [ "python", "src/main.py" ]
