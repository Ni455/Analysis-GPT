#!/usr/bin/env bash
# deploy/setup.sh — One-shot EC2 first-time setup for Analysis-GPT
# Run as: bash setup.sh
set -e

REPO_URL="https://github.com/Ni455/Analysis-GPT.git"
APP_DIR="/home/ubuntu/Analysis-GPT"
SERVICE="analysis-gpt"

echo "==> Updating system packages"
sudo apt-get update -y
sudo apt-get install -y python3.11 python3.11-venv python3-pip git

echo "==> Cloning repo"
if [ -d "$APP_DIR" ]; then
  echo "   Directory exists — pulling latest"
  cd "$APP_DIR" && git pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "==> Creating virtual environment"
python3.11 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Creating .env file"
if [ ! -f "$APP_DIR/.env" ]; then
  read -p "Enter your Telegram BOT_TOKEN: " BOT_TOKEN
  read -p "Enter your ALLOWED_USER_ID: " USER_ID
  cat > "$APP_DIR/.env" <<EOF
BOT_TOKEN=${BOT_TOKEN}
ALLOWED_USER_ID=${USER_ID}
EOF
  echo "   .env created"
else
  echo "   .env already exists — skipping"
fi

echo "==> Installing systemd service"
sudo cp "$APP_DIR/deploy/analysis-gpt.service" "/etc/systemd/system/${SERVICE}.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"

echo "==> Granting passwordless sudo for systemctl restart (needed by /update command)"
SUDOERS_LINE="ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE}"
if ! sudo grep -qF "$SUDOERS_LINE" /etc/sudoers; then
  echo "$SUDOERS_LINE" | sudo tee -a /etc/sudoers > /dev/null
  echo "   sudoers rule added"
fi

echo ""
echo "✅ Setup complete!"
echo "   Check bot status: sudo systemctl status ${SERVICE}"
echo "   View logs:        journalctl -u ${SERVICE} -f"
