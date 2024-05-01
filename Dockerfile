FROM python:3.11
# FROM python:3.12-slim

WORKDIR /app

COPY . .


WORKDIR /app/test/AI-Agent-Code-Generator
RUN pip install -r requirements.txt --no-cache-dir

ENV OPENAI_TOKEN=${OPENAI_TOKEN}
ENV LOCALLLM_TOKEN=${LOCALLLM_TOKEN}
ENV LOCALLLM_BASEURL=${LOCALLLM_BASEURL}
ENV LLAMA_CLOUD_API_KEY=${LLAMA_CLOUD_API_KEY}

# ENTRYPOINT [ "python", "src/main.py" ]
ENTRYPOINT [ "python", "main.py" ]