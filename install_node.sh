#!/bin/bash
# Install Node.js and npm

set -e

echo "=== Installing Node.js and npm ==="
echo ""

# Check if already installed
if command -v node &> /dev/null && command -v npm &> /dev/null; then
    echo "✅ Node.js and npm are already installed"
    node --version
    npm --version
    exit 0
fi

echo "Installing Node.js 18.x..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

echo ""
echo "Verifying installation..."
node --version
npm --version

echo ""
echo "✅ Node.js and npm installed successfully!"
echo ""
echo "Now you can start the frontend with:"
echo "  cd dashboard && npm install && npm run dev"

