#!/usr/bin/env bash
# setup.sh — Install & configure TOR IP Rotator on Kali Linux
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

banner() { echo -e "\n${CYAN}╔══════════════════════════════════════════╗
║   TOR IP ROTATOR — Kali Linux Setup      ║
╚══════════════════════════════════════════╝${NC}\n"; }

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[-]${NC} $*"; exit 1; }

banner

# ── Root check ────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Run as root: sudo bash setup.sh"

# ── System packages ───────────────────────────────────────────────────────
info "Updating package list…"
apt-get update -qq

info "Installing Tor and dependencies…"
apt-get install -y -qq tor python3 python3-pip curl

# ── Python deps ───────────────────────────────────────────────────────────
info "Installing Python packages…"
pip3 install -r requirements.txt --quiet

# ── torrc config ──────────────────────────────────────────────────────────
info "Configuring /etc/tor/torrc…"

TORRC=/etc/tor/torrc
HASHED=$(tor --hash-password "torpassword" 2>/dev/null | tail -1)

if ! grep -q "ControlPort 9051" "$TORRC" 2>/dev/null; then
    cat >> "$TORRC" <<EOF

# ── Added by TOR IP Rotator ──
ControlPort 9051
HashedControlPassword ${HASHED}
SocksPort 9050
MaxCircuitDirtiness 3
EOF
    info "torrc updated."
else
    warn "torrc already configured — skipping."
fi

# ── Log dir ───────────────────────────────────────────────────────────────
info "Creating log directory…"
mkdir -p logs
touch logs/ip.txt

# ── Systemd service ───────────────────────────────────────────────────────
info "Installing systemd service…"
SCRIPT_DIR="$(pwd)"

cat > /etc/systemd/system/tor-rotator.service <<EOF
[Unit]
Description=TOR IP Rotator Dashboard
After=network.target tor.service

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/dashboard.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable tor-rotator.service 2>/dev/null || true

# ── Start Tor ─────────────────────────────────────────────────────────────
info "Starting Tor service…"
service tor restart
sleep 2

TOR_OK=$(curl -s --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null || echo "")
if echo "$TOR_OK" | grep -q '"IsTor":true'; then
    info "Tor is running and connected!"
else
    warn "Tor may not be fully connected yet. Check: service tor status"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo -e "  Start dashboard:  ${CYAN}python3 dashboard.py${NC}"
echo -e "  Or use systemd:   ${CYAN}systemctl start tor-rotator${NC}"
echo -e "  Open browser:     ${CYAN}http://127.0.0.1:5000${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""
