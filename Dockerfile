# FROM python:3.11
FROM python:3.12-slim

WORKDIR /app

RUN apt update; apt install -y pulseaudio libportaudio2 alsa-utils sox libsox-fmt-all espeak-ng cmake nano

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

ENV OPENAI_TOKEN=${OPENAI_TOKEN}
ENV LOCALLLM_TOKEN=${LOCALLLM_TOKEN}
ENV LOCALLLM_BASEURL=${LOCALLLM_BASEURL}
ENV LLAMA_CLOUD_API_KEY=${LLAMA_CLOUD_API_KEY}
ENV PULSE_SERVER=host.docker.internal

COPY . .

ENTRYPOINT [ "python", "src/main.py" ]
