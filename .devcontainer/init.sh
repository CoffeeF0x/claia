#!/bin/bash
set -e

sudo apt-get update && sudo apt-get install -y build-essential && sudo rm -rf /var/lib/apt/lists/*

pip install --disable-pip-version-check --no-cache-dir -r build/requirements.txt
pip install -e .
