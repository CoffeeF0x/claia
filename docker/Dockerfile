# Set binary name as build argument with default value
ARG BINARY_NAME=claia

# BUILD STAGE
FROM python:3.12-slim AS builder

# Make ARG available in this stage
ARG BINARY_NAME

WORKDIR /build

# Copy build requirements
COPY build.sh .
COPY requirements.txt .
COPY src/ src/

# Make script executable and run build
RUN chmod +x build.sh && ./build.sh ${BINARY_NAME}



# DISTRIBUTION STAGE
FROM debian:stable-slim

# Make ARG available in this stage and create ENV for runtime
ARG BINARY_NAME
ENV BINARY_NAME=${BINARY_NAME}

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
  pulseaudio \
  libportaudio2 \
  alsa-utils \
  sox \
  libsox-fmt-all \
  espeak-ng \
  sshpass \
  && rm -rf /var/lib/apt/lists/*

# Copy the compiled binary from builder
COPY --from=builder /build/dist/${BINARY_NAME} .

# Use the compiled binary
ENTRYPOINT ["/bin/sh", "-c", "exec ./${BINARY_NAME}"]
