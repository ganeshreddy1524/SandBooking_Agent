#!/bin/bash
# ----------------------------------------------------
# Sand Availability Agent - GCP 24/7 Auto-Deployment
# ----------------------------------------------------
set -e

echo "🚀 Installing dependencies and setting up Sand Monitor Agent on GCP VM..."

# Update package lists and install python, pip, git
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

# Set up project directory
PROJECT_DIR="$(pwd)"

# Create virtual environment if not present
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtualenv and install python packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service for 24/7 background execution & auto-restart
SERVICE_FILE="/etc/systemd/system/sand_agent.service"

sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Telangana Sand Availability Notifier AI Agent
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd daemon and enable service
sudo systemctl daemon-reload
sudo systemctl enable sand_agent.service
sudo systemctl restart sand_agent.service

echo "✅ Sand Availability Agent is now running 24/7 on your GCP VM!"
echo "📊 Check service status with: sudo systemctl status sand_agent"
echo "📜 View live logs with    : sudo journalctl -u sand_agent -f"
