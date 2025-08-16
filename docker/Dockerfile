FROM python:3.12-slim

WORKDIR /app

RUN apt update && apt install -y \
  nano \
  sshpass \
  git

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY src/ src/
COPY pyproject.toml .
COPY .env .
COPY deploy.sh .

# Ensure local packages are installed
RUN pip install -e .

CMD [ "python", "src" ]