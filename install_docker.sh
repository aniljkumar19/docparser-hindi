#!/bin/bash
# Install Docker and Docker Compose

set -e

echo "=== Installing Docker ==="
echo ""

# Check if already installed
if command -v docker &> /dev/null; then
    echo "✅ Docker is already installed: $(docker --version)"
else
    echo "Installing Docker..."
    sudo apt update
    sudo apt install -y docker.io docker-compose
fi

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose is installed: $(docker-compose --version)"
elif docker compose version &> /dev/null; then
    echo "✅ docker compose (plugin) is available: $(docker compose version)"
else
    echo "⚠️  docker-compose not found, but continuing..."
fi

# Start Docker service
echo ""
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
echo ""
echo "Adding $USER to docker group..."
sudo usermod -aG docker $USER

echo ""
echo "✅ Docker installation complete!"
echo ""
echo "⚠️  IMPORTANT: You need to log out and log back in for group changes to take effect."
echo "   Or run: newgrp docker"
echo ""
echo "After that, run:"
echo "  cd /home/vncuser/apps/docparser"
echo "  docker-compose up -d db redis minio"
echo ""

