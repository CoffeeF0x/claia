FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt --no-cache-dir

ENV OPENAI_TOKEN=${OPENAI_TOKEN}
ENV LOCALLLM_TOKEN=${LOCALLLM_TOKEN}
ENV LOCALLLM_BASEURL=${LOCALLLM_BASEURL}

ENTRYPOINT [ "python", "src/main.py" ]