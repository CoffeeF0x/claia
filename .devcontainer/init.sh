#!/bin/bash
set -e

apt-get update
apt-get install -y build-essential
rm -rf /var/lib/apt/lists/*

pip install --disable-pip-version-check --no-cache-dir -e ".[dev]"
