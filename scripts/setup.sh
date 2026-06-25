#!/bin/bash
# FaceStream Setup Script

set -e

echo "=== FaceStream Setup ==="
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# Install dependencies
echo "Installing dependencies..."
uv sync

# Check for Modal
if ! command -v modal &> /dev/null; then
    echo "Installing Modal..."
    uv add modal
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To deploy:"
echo "  uv run modal deploy -m facestream.main"
echo ""
echo "To serve locally:"
echo "  uv run modal serve facestream.main"
