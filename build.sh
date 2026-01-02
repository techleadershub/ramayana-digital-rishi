#!/bin/bash
# Build script to install CPU-only PyTorch for smaller image size

set -e

echo "Installing CPU-only PyTorch (reduces image size by ~1.5GB)..."
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu

echo "Installing other dependencies..."
pip install -r requirements.txt

