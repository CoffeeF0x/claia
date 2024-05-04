FROM python:3.11
# FROM python:3.12-slim

WORKDIR /app

COPY data .
COPY history .
COPY src .
COPY requirements.txt .
COPY requirements-llamaindex.txt .
# COPY . .

RUN apt update; apt install -y pulseaudio libportaudio2 alsa-utils sox libsox-fmt-all espeak-ng cmake nano

RUN pip install -r requirements.txt --no-cache-dir
RUN pip install -r requirements-llamaindex.txt --no-cache-dir
# WORKDIR /app/test/AI-Agent-Code-Generator

ENV OPENAI_TOKEN=${OPENAI_TOKEN}
ENV LOCALLLM_TOKEN=${LOCALLLM_TOKEN}
ENV LOCALLLM_BASEURL=${LOCALLLM_BASEURL}
ENV LLAMA_CLOUD_API_KEY=${LLAMA_CLOUD_API_KEY}
ENV PULSE_SERVER=host.docker.internal

ENV LLAMACPP_VERSION="b2700"

RUN wget "https://github.com/ggerganov/llama.cpp/archive/refs/tags/${LLAMACPP_VERSION}.zip"
RUN unzip "${LLAMACPP_VERSION}.zip" -d /llama.cpp
RUN rm "${LLAMACPP_VERSION}.zip"

WORKDIR /llama.cpp/llama.cpp-${LLAMACPP_VERSION}/build
RUN cmake ..
RUN cmake --build . --config Release
RUN mv bin /llama.cpp/bin

WORKDIR /app

ENV WHISPERCPP_VERSION="1.5.5"

RUN wget "https://github.com/ggerganov/whisper.cpp/archive/refs/tags/v${WHISPERCPP_VERSION}.zip"
RUN unzip "v${WHISPERCPP_VERSION}.zip" -d /whisper.cpp
RUN rm "v${WHISPERCPP_VERSION}.zip"

WORKDIR /whisper.cpp/whisper.cpp-${WHISPERCPP_VERSION}
RUN make libwhisper.so

WORKDIR /app

RUN wget "https://github.com/dnhkng/GlaDOS/archive/refs/heads/main.zip"
RUN unzip main.zip -d /GlaDOS
RUN rm main.zip

ENTRYPOINT [ "python", "src/main.py" ]
# ENTRYPOINT [ "python", "main.py" ]