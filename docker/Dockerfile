FROM python:3.12-slim

WORKDIR /app

RUN apt update && apt install -y \
  zip \
  nano \
  sshpass \
  git \
  htop

COPY build/ build/
RUN pip install -r build/requirements.txt --no-cache-dir

COPY src/ src/
COPY pyproject.toml .
COPY .env .

# RUN /app/build/deploy.sh --export --dist-dir /app/dist
RUN pip install -e .

CMD [ "python", "-m", "claia" ]