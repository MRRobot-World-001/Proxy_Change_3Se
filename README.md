# 🧅 TOR IP ROTATOR — Kali Linux

[![CI](https://github.com/MRRobot-World-001/Proxy_Change_3Se.git)](https://github.com/YOUR_USERNAME/tor-ip-rotator/actions)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-green)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A **Kali Linux** tool that automatically rotates your Tor exit-node IP every **3 seconds**, cycling through 43 countries. Includes a live **cyberpunk web dashboard** with real-time SSE log streaming and persistent IP logging to `logs/ip.txt`.

---

## 📸 Dashboard Preview

```
╔══════════════════════════════════════════════╗
║   TOR IP ROTATOR  —  Live Dashboard          ║
║   http://127.0.0.1:5000                      ║
╚══════════════════════════════════════════════╝
  CURRENT EXIT NODE: 185.220.101.47
  Country: 🇩🇪 DE | City: Frankfurt | Org: AS24940 Hetzner
  Rotations: 142 | Interval: 3s | Stream: LIVE
```

---

## 🗂️ Repository Structure

```
tor-ip-rotator/
├── tor_rotator.py          # Core rotation engine (stem + Tor control)
├── dashboard.py            # Flask web server + SSE event stream
├── templates/
│   └── index.html          # Cyberpunk live dashboard UI
├── logs/
│   ├── .gitkeep
│   └── ip.txt              # JSONL log (created at runtime)
├── tests/
│   └── test_rotator.py     # Pytest unit tests
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI
├── setup.sh                # One-command Kali install script
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/tor-ip-rotator.git
cd tor-ip-rotator
```

### 2. Run Setup (as root)

```bash
sudo bash setup.sh
```

This will:
- Install `tor`, `python3`, `pip` via apt
- Install Python requirements (`stem`, `flask`, `requests`, `PySocks`)
- Configure `/etc/tor/torrc` with `ControlPort 9051` and a hashed password
- Create a systemd service (`tor-rotator.service`)
- Verify Tor connectivity

### 3. Start Dashboard

```bash
python3 dashboard.py
```

Open **http://127.0.0.1:5000** in your browser, then click **▶ START ROTATION**.

---

## ⚙️ Manual Tor Setup

If you prefer to configure Tor manually:

```bash
sudo apt install tor
```

Add to `/etc/tor/torrc`:

```
ControlPort 9051
HashedControlPassword <output of: tor --hash-password yourpassword>
SocksPort 9050
MaxCircuitDirtiness 3
CookieAuthentication 1
```

Set your password in `tor_rotator.py`:

```python
TOR_PASSWORD = "yourpassword"
```

Restart Tor:

```bash
sudo service tor restart
```

---

## 📡 API Endpoints

| Method | Endpoint         | Description                              |
|--------|------------------|------------------------------------------|
| GET    | `/`              | Web dashboard                            |
| GET    | `/api/status`    | Rotator status JSON                      |
| POST   | `/api/start`     | Start IP rotation                        |
| POST   | `/api/stop`      | Stop IP rotation                         |
| GET    | `/api/logs`      | Last 200 log entries (JSON)              |
| GET    | `/api/logs/raw`  | Raw `ip.txt` content (plain text)        |
| GET    | `/stream`        | SSE stream for real-time log events      |

---

## 📄 Log Format (`logs/ip.txt`)

Each line is a JSON record:

```json
{
  "timestamp": "2025-01-15 12:34:56 UTC",
  "level": "INFO",
  "message": "New IP: 185.220.101.47 | Frankfurt, DE | AS24940 Hetzner Online GmbH",
  "ip_info": {
    "ip": "185.220.101.47",
    "city": "Frankfurt",
    "region": "Hesse",
    "country": "DE",
    "org": "AS24940 Hetzner Online GmbH",
    "timezone": "Europe/Berlin"
  },
  "target_country": "de"
}
```

---

## 🌍 Supported Countries (43)

`US DE FR NL GB CH SE NO CA JP AU BR SG IN RU PL IT ES AT BE CZ DK FI GR HU IE KR MX NZ PT RO ZA AR CL CO EG ID MY PH TH TR UA VN`

> Note: Tor uses exit-node hints (`ExitNodes {cc}`). Country availability depends on the current Tor relay network. The rotator will skip unavailable exits automatically.

---

## 🔧 Configuration

Edit at the top of `tor_rotator.py`:

| Variable            | Default       | Description                        |
|---------------------|---------------|------------------------------------|
| `TOR_CONTROL_PORT`  | `9051`        | Tor control port                   |
| `TOR_SOCKS_PORT`    | `9050`        | Tor SOCKS proxy port               |
| `TOR_PASSWORD`      | `torpassword` | Must match torrc hash              |
| `ROTATE_INTERVAL`   | `3`           | Seconds between rotations          |
| `LOG_FILE`          | `logs/ip.txt` | Log file path                      |
| `COUNTRIES`         | 43 countries  | Rotation list                      |

---

## 🧪 Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## 🚀 GitHub Push

```bash
git init
git add .
git commit -m "feat: initial TOR IP rotator with live dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/tor-ip-rotator.git
git push -u origin main
```

---

## ⚠️ Disclaimer

This tool is for **educational and privacy purposes only**. Use responsibly and in compliance with your local laws. The Tor network should not be used for illegal activities.

---

## 📜 License

MIT © 2025
