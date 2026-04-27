# iridiumSBD

Utilities for receiving, validating, saving, and inspecting Iridium Short Burst Data (SBD) DirectIP messages.

This repository is used as a production DirectIP listener. The instructions below are intentionally written for running the repository **as-is** without changing the existing code layout or imports.

---

## What this repo does

The repository provides:

- A TCP DirectIP listener for incoming Iridium SBD messages.
- Basic validation of received ISBD binary messages.
- Automatic saving of valid messages to an `inbox/` directory.
- Automatic saving of invalid/corrupted messages to a `corrupted/` directory.
- Optional post-processing hook that runs an external command/script after a valid inbound message is saved.
- A small dump utility for inspecting saved `.isbd` files.

The listener is implemented in:

```text
iridiumSBD/directip/server.py
```

The CLI wrapper is implemented in:

```text
iridiumSBD/cli.py
```

The message parsing and validation helpers are implemented in:

```text
iridiumSBD/iridiumSBD.py
```

---

## Repository layout

```text
iridiumSBD/
├── README.rst
├── requirements.txt
├── setup.py
├── iridiumSBD/
│   ├── cli.py
│   ├── iridiumSBD.py
│   ├── __init__.py
│   └── directip/
│       ├── __init__.py
│       └── server.py
└── tests/
```

**Important:** Commands must be run from the inner package directory:

```bash
~/iridiumSBD/iridiumSBD
```

This directory contains both:

```text
iridiumSBD.py
directip/server.py
```

which allows the current imports to resolve correctly.

---

## Server prerequisites

Recommended baseline:

- Linux server or VM
- Python 3
- Network access from the Iridium DirectIP gateway
- Open inbound TCP port (default: `10800`)
- Writable data directory
- Optional: dedicated Linux user

---

## Clone the repository

```bash
cd ~
git clone <REPO_URL> iridiumSBD
cd ~/iridiumSBD
```

---

## Create a Python environment

```bash
cd ~/iridiumSBD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

If `psycopg2` fails:

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3-dev libpq-dev
python -m pip install -r requirements.txt
```

---

## ⚠️ Important: How this repo is intended to run

This repository is **not designed to be run via `pip install` or global CLI execution**.

It is intended to be run directly from the cloned repository:

```bash
cd ~/iridiumSBD/iridiumSBD
python cli.py ...
```

---

## Create runtime directories

```bash
sudo mkdir -p /opt/iridiumSBD/data
sudo mkdir -p /var/log/iridiumSBD
sudo chown -R "$USER":"$USER" /opt/iridiumSBD /var/log/iridiumSBD
```

Directories used:

```text
/opt/iridiumSBD/data/inbox
/opt/iridiumSBD/data/corrupted
```

---

## Run the DirectIP listener manually

```bash
cd ~/iridiumSBD
source .venv/bin/activate
cd ~/iridiumSBD/iridiumSBD

python cli.py \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data
```

---

## Optional outbound forwarding

```bash
python cli.py \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data \
  --iridium-host=<HOST> \
  --iridium-port=10800
```

---

## Optional post-processing hook

```bash
python cli.py \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data \
  --post-processing=/opt/iridiumSBD/bin/process_isbd.sh
```

Example script:

```bash
#!/usr/bin/env bash
set -euo pipefail

ISBD_FILE="$1"
echo "Received ISBD file: ${ISBD_FILE}" >> /var/log/iridiumSBD/postprocess.log
```

---

## Run as a systemd service

```bash
sudo nano /etc/systemd/system/iridiumSBD-directip.service
```

```ini
[Unit]
Description=Iridium SBD DirectIP Listener
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<LINUX_USER>
Group=<LINUX_GROUP>
WorkingDirectory=/home/<LINUX_USER>/iridiumSBD/iridiumSBD

ExecStart=/home/<LINUX_USER>/iridiumSBD/.venv/bin/python \
  /home/<LINUX_USER>/iridiumSBD/iridiumSBD/cli.py \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable iridiumSBD-directip.service
sudo systemctl start iridiumSBD-directip.service
```

---

## Firewall configuration

```bash
sudo ufw allow 10800/tcp
```

---

## Verify listener

```bash
ss -ltnp | grep 10800
tail -f /var/log/iridiumSBD/directip.log
```

---

## Dump a saved message

```bash
cd ~/iridiumSBD
source .venv/bin/activate
cd ~/iridiumSBD/iridiumSBD

python cli.py dump /opt/iridiumSBD/data/inbox/<FILE>.isbd
```

---

## Operational notes

- Always run from: `~/iridiumSBD/iridiumSBD`
- Use absolute paths
- Ensure write permissions
- Open firewall ports
- Use `0.0.0.0` for external access

---

## Troubleshooting

### ModuleNotFoundError: directip

```bash
cd ~/iridiumSBD/iridiumSBD
python cli.py ...
```

### ImportError: dump

Same fix — run from inner directory.

### Address already in use

```bash
sudo ss -ltnp | grep 10800
```

### No files in inbox

Check:

- Listener running
- Firewall open
- Correct port/IP
- Directory permissions

### Messages in corrupted/

Input is not valid ISBD format.

---

## Recommended handoff checklist

Provide:

- Repo URL + branch
- Python version
- OS
- Port + firewall rules
- Data directory path
- Sample `.isbd` (if safe)
- Any post-processing scripts

---

## Production note

This README reflects the repository **as-is**.

The most important requirement:

👉 Run `cli.py` from the inner package directory so imports resolve correctly.
