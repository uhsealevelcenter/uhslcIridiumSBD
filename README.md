# iridiumSBD

Utilities for receiving, validating, saving, inspecting, extracting, and decoding Iridium Short Burst Data (SBD) DirectIP messages.

This repository can run a TCP DirectIP listener, save full binary `.isbd` messages, and optionally post-process inbound mobile-originated messages into raw payload files and decoded UHSLC pseudobinary-C CSV output.

---

## What this repo does

- Runs a TCP DirectIP listener for incoming Iridium SBD messages.
- Validates and saves complete DirectIP binary messages.
- Saves valid messages under `data/inbox/`.
- Saves invalid/corrupted messages under `data/corrupted/`.
- Sends the required DirectIP acknowledgement for inbound messages.
- Supports an optional post-processing command after each inbound message is saved.
- Extracts MO payloads from saved `.isbd` files.
- Decodes already-extracted UHSLC pseudobinary-C payload text to CSV.
- Provides one end-to-end postprocessor for `.isbd → raw payload → decoded CSV → archive`.

---

## Repository layout

```text
uhslcIridiumSBD/
├── README.md
├── requirements.txt
├── setup.py
├── iridiumSBD/
│   ├── __init__.py
│   ├── cli.py
│   ├── iridiumSBD.py
│   ├── bin/
│   │   ├── postproc.py          # compatibility wrapper
│   │   └── start_server         # example launcher
│   ├── decode/
│   │   ├── __init__.py
│   │   ├── cli.py               # standalone pseudobinary-C decoder CLI
│   │   ├── decodeit.py          # legacy standalone decoder script
│   │   └── pseudobinary_c_decoder.py
│   ├── directip/
│   │   ├── __init__.py
│   │   └── server.py
│   └── processing/
│       ├── __init__.py
│       └── postprocess_isbd.py  # production .isbd postprocessor
└── tests/
```

The key modules are:

```text
iridiumSBD/directip/server.py          DirectIP TCP listener
iridiumSBD/cli.py                      Main listener/dump CLI
iridiumSBD/iridiumSBD.py               DirectIP message parsing/validation
iridiumSBD/processing/postprocess_isbd.py  End-to-end .isbd postprocessor
iridiumSBD/decode/pseudobinary_c_decoder.py Pseudobinary-C decoder library
iridiumSBD/decode/cli.py               CLI for already-extracted payload text
```

---

## Requirements

Runtime dependency:

```text
Click>=6.7
```

The pseudobinary-C decoding and postprocessing code uses the Python standard library only.

Recommended baseline:

- Linux server or VM
- Python 3.8+
- Network access from the Iridium DirectIP gateway
- Open inbound TCP port, commonly `10800`
- Writable runtime data directory
- Optional dedicated Linux user

---

## Install for development or deployment

```bash
git clone <REPO_URL> iridiumSBD
cd iridiumSBD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

This installs console commands:

```text
iridium-sbd              Main DirectIP listener/dump CLI
iridiumSBD               Backward-compatible alias for the main CLI
iridium-sbd-postprocess  End-to-end .isbd postprocessor
iridium-sbd-decode       Decoder for already-extracted pseudobinary-C text files
```

Verify:

```bash
iridium-sbd --help
iridium-sbd-postprocess --help
iridium-sbd-decode --help
```

---

## Runtime directories

Example production layout:

```bash
sudo mkdir -p /opt/iridiumSBD/data
sudo mkdir -p /var/log/iridiumSBD
sudo chown -R "$USER":"$USER" /opt/iridiumSBD /var/log/iridiumSBD
```

The listener/postprocessor use this structure:

```text
/opt/iridiumSBD/data/inbox/       Saved valid DirectIP .isbd files
/opt/iridiumSBD/data/corrupted/   Invalid/corrupted DirectIP messages
/opt/iridiumSBD/data/raw/YYYYMMDD/ Extracted MO payload copies
/opt/iridiumSBD/data/csv/         Decoded station/year CSV files
/opt/iridiumSBD/data/archive/YYYYMMDD/ Processed .isbd files
/opt/iridiumSBD/data/empty/       Valid .isbd files without MO payloads
/opt/iridiumSBD/data/error/       Messages that failed postprocessing
```

---

## Run the DirectIP listener

```bash
source .venv/bin/activate

iridium-sbd \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data
```

Valid messages are saved to:

```text
/opt/iridiumSBD/data/inbox/<timestamp>_<client-ip>.isbd
```

Invalid messages are saved to:

```text
/opt/iridiumSBD/data/corrupted/
```

---

## Run listener with end-to-end postprocessing

This is the recommended production flow for UHSLC pseudobinary-C payloads:

```text
DirectIP gateway
  → listener saves full binary .isbd file
  → postprocessor extracts MO payload
  → raw payload copy is saved
  → pseudobinary-C payload is decoded to CSV
  → original .isbd is archived
```

Command:

```bash
source .venv/bin/activate

iridium-sbd \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data \
  --post-processing=/home/<USER>/iridiumSBD/.venv/bin/iridium-sbd-postprocess
```

Use the absolute path to `iridium-sbd-postprocess` from the virtual environment. The listener passes the saved `.isbd` filename as the only argument.

Output examples:

```text
/opt/iridiumSBD/data/raw/20260427/20260427123456-300234060000000.raw
/opt/iridiumSBD/data/csv/<station>_2026.csv
/opt/iridiumSBD/data/archive/20260427/<original>.isbd
```

If a valid message has no MO payload, it is moved to `data/empty/`. If postprocessing fails, the `.isbd` file is moved to `data/error/`.

---

## Manually postprocess one saved `.isbd` file

```bash
iridium-sbd-postprocess /opt/iridiumSBD/data/inbox/<FILE>.isbd
```

Useful options:

```bash
iridium-sbd-postprocess /opt/iridiumSBD/data/inbox/<FILE>.isbd \
  --data-dir=/opt/iridiumSBD/data \
  --output-dir=/opt/iridiumSBD/data/csv \
  --year=2026
```

Extract raw payload only, without pseudobinary-C decoding:

```bash
iridium-sbd-postprocess /opt/iridiumSBD/data/inbox/<FILE>.isbd --raw-only
```

Leave the `.isbd` file in place while testing:

```bash
iridium-sbd-postprocess /opt/iridiumSBD/data/inbox/<FILE>.isbd --no-archive
```

---

## Decode an already-extracted pseudobinary-C payload file

Use this when you already have a text payload file, not a full binary `.isbd` DirectIP file.

Expected input shape:

```text
<pseudobinary-c-data> <station-name>
```

Example:

```bash
iridium-sbd-decode /path/to/payload.raw \
  --output-dir=/opt/iridiumSBD/data/csv \
  --year=2026
```

Important distinction:

- `iridium-sbd-postprocess` expects a full binary DirectIP `.isbd` file.
- `iridium-sbd-decode` expects already-extracted pseudobinary-C payload text.

---

## Dump a saved `.isbd` message

```bash
iridium-sbd dump /opt/iridiumSBD/data/inbox/<FILE>.isbd
```

Show IMEI only:

```bash
iridium-sbd dump --imei /opt/iridiumSBD/data/inbox/<FILE>.isbd
```

---

## Optional outbound forwarding

```bash
iridium-sbd \
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

## Example systemd service

Create:

```bash
sudo nano /etc/systemd/system/iridiumSBD-directip.service
```

Example service:

```ini
[Unit]
Description=Iridium SBD DirectIP Listener
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<LINUX_USER>
Group=<LINUX_GROUP>
WorkingDirectory=/home/<LINUX_USER>/iridiumSBD

ExecStart=/home/<LINUX_USER>/iridiumSBD/.venv/bin/iridium-sbd \
  --loglevel=info \
  --logfile=/var/log/iridiumSBD/directip.log \
  listen \
  --host=0.0.0.0 \
  --port=10800 \
  --datadir=/opt/iridiumSBD/data \
  --post-processing=/home/<LINUX_USER>/iridiumSBD/.venv/bin/iridium-sbd-postprocess

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable iridiumSBD-directip.service
sudo systemctl start iridiumSBD-directip.service
```

Check status/logs:

```bash
sudo systemctl status iridiumSBD-directip.service
journalctl -u iridiumSBD-directip.service -f
tail -f /var/log/iridiumSBD/directip.log
```

---

## Firewall

Example with UFW:

```bash
sudo ufw allow 10800/tcp
```

Verify listener:

```bash
ss -ltnp | grep 10800
```

---

## Developer notes

Run tests:

```bash
python -m pytest
```

Build a source distribution:

```bash
python -m pip install build
python -m build
```

The production postprocessing entry point is intentionally separate from the lower-level decoder:

- Keep `iridiumSBD.decode.pseudobinary_c_decoder.PseudobinaryCDecoder` as the reusable decoder library.
- Use `iridium-sbd-decode` for already-extracted text payloads.
- Use `iridium-sbd-postprocess` for full listener output files.

---

## Troubleshooting

### No files appear in `inbox/`

Check:

- Listener is running.
- Correct host/IP and port are configured with the Iridium gateway.
- Firewall allows inbound TCP traffic.
- Data directory exists and is writable.

### Files appear in `corrupted/`

The listener received data that did not validate as a complete DirectIP SBD message.

### Files appear in `error/`

The message was valid DirectIP but failed postprocessing. Common causes:

- Payload is not UTF-8 text.
- Payload is not UHSLC pseudobinary-C format.
- Output directory is not writable.
- The wrong postprocessor was used for the file type.

### Decoder produces the wrong year

Pass the year explicitly:

```bash
iridium-sbd-postprocess /path/to/file.isbd --year=2026
iridium-sbd-decode /path/to/payload.raw --year=2026
```

This matters for historical files and for files processed near a year boundary.

---

## External handoff checklist

Before sharing with an external agency, provide:

- Repo URL and branch/tag.
- Python version.
- OS/runtime environment.
- DirectIP host/port/firewall details.
- Runtime data directory path.
- Whether the agency should run raw listener only or listener plus postprocessing.
- A safe sample `.isbd` file, if available.
- A safe sample extracted payload and decoded CSV, if available.
