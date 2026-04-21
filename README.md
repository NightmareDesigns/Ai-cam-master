# 🎯 AI-Cam

**AI-Cam** is an open-source, self-hosted AI-powered security camera monitoring system — built for private use and shareware. It provides the core features of commercial platforms like Coram AI, running entirely on your own hardware without any cloud subscription.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-orange)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📷 **Multi-camera support** | RTSP streams, USB webcams, HTTP MJPEG — add unlimited cameras |
| 🔍 **Auto-discovery with credential brute-forcing** | Automatically finds cameras on your network and tests 50+ default credentials to identify valid logins — runs on startup |
| 🔑 **Vendor logins** | Built-in helpers for Zmodo (local + cloud), Blink (cloud), EseeCam/EseeCloud, and Geeni/Tuya (with LAN discovery + RTSP or snapshot liveview) |
| ☁️ **Cloud camera access** | Access Zmodo cameras via user.zmodo.com cloud and Blink cameras via cloud liveview — no local network required |
| 🤖 **AI Object Detection** | YOLOv8 real-time detection of persons, vehicles, animals, and 80+ COCO classes |
| 🏃 **Motion Detection** | Background-subtraction motion detection (no AI needed) |
| 📡 **Live Streaming** | MJPEG HTTP stream + WebSocket binary frames per camera |
| 📸 **Event Snapshots** | Annotated JPEG saved on every detection with bounding boxes |
| 🔔 **Alert Rules** | Per-camera or global rules, triggering on any class or event type |
| 📧 **Notifications** | Console, email (SMTP), and webhook (POST JSON) |
| 🖥️ **Web Dashboard** | Dark-themed dashboard with live camera tiles and event timeline |
| 🗄️ **Local Storage** | SQLite database — no external services needed |
| 🐳 **Docker support** | Single-command deployment with docker-compose |
| 📚 **REST API** | Full OpenAPI/Swagger documentation at `/docs` |

---

## 🚀 Quick Start

### Option A — Local Python

```bash
# 1. Clone
git clone https://github.com/NightmareDesigns/Ai-cam-master.git
cd Ai-cam-master

# 2. Create virtualenv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (copy and edit as needed)
cp .env.example .env

# 5. Run
python run.py
```

Open **http://localhost:8000** in your browser.

### Option B — Docker

```bash
cp .env.example .env
docker-compose up -d
```

Open **http://localhost:8000** in your browser.

---

## 🖼️ Dashboard Overview

```
┌─────────────────────────────────────────────────────────┐
│  🎯 AI-Cam                                              │
├──────────┬──────────────────────────────────────────────┤
│ 🏠 Home  │  Dashboard                                   │
│ 📷 Cams  │  ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│ 🔔 Events│  │ Total Cams│ │  Online   │ │  Events   │  │
│ ⚙️ Sett. │  │     4     │ │     3     │ │    17     │  │
│ 📄 API   │  └───────────┘ └───────────┘ └───────────┘  │
│          │                                              │
│          │  Live Cameras                                │
│          │  ┌─────────────┐ ┌─────────────┐           │
│          │  │ Front Door  │ │  Parking    │           │
│          │  │  [LIVE IMG] │ │  [LIVE IMG] │           │
│          │  │ ●Live AI    │ │ ●Live AI    │           │
│          │  └─────────────┘ └─────────────┘           │
│          │                                              │
│          │  Recent Events                               │
│          │  [snapshot] Front Door  person  92%  2m ago │
│          │  [snapshot] Parking     car     87%  5m ago │
└──────────┴──────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

All settings are controlled via environment variables or a `.env` file:

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | HTTP port |
| `DEBUG` | `false` | Enable hot-reload (dev only) |
| `DATABASE_URL` | `sqlite:///./aicam.db` | SQLAlchemy DB URL |
| `RECORDINGS_DIR` | `./recordings` | Video clip output directory |
| `SNAPSHOTS_DIR` | `./snapshots` | Snapshot JPEG output directory |
| `YOLO_MODEL` | `yolov8n.pt` | YOLOv8 model variant (`n/s/m/l/x`) |
| `DETECTION_CONFIDENCE` | `0.45` | Minimum detection confidence (0–1) |
| `TRACKED_CLASSES` | `person,car,…` | Comma-separated COCO class names to track |
| `STREAM_FPS` | `10` | Target frames per second for live streams |
| `ALERT_COOLDOWN_SECONDS` | `30` | Minimum seconds between repeated alerts |
| `SMTP_HOST` | — | SMTP server for email alerts |
| `ALERT_EMAIL_TO` | — | Destination email address for alerts |

### Auto-Discovery Settings

| Variable | Default | Description |
|---|---|---|
| `AUTO_DISCOVERY_ENABLED` | `true` | Enable automatic camera discovery |
| `AUTO_DISCOVERY_ON_STARTUP` | `true` | Run discovery automatically when the application starts |
| `AUTO_DISCOVERY_BRUTE_FORCE` | `true` | Test common default credentials on discovered cameras |
| `AUTO_DISCOVERY_AUTO_ADD` | `true` | Automatically add discovered cameras to the database |
| `AUTO_DISCOVERY_MAX_HOSTS` | `256` | Maximum number of hosts to scan (normal mode) |
| `AUTO_DISCOVERY_TIMEOUT` | `2.0` | Timeout in seconds for each camera probe |
| `AUTO_DISCOVERY_INTERVAL_HOURS` | `24` | Hours between automatic re-scans (0 = no re-scan) |
| `AUTO_DISCOVERY_SUBNETS` | — | Comma-separated subnets (e.g., `192.168.1.0/24`), leave empty to auto-detect |
| `AUTO_DISCOVERY_FULL_SWEEP` | `false` | Enable full IP sweep mode (scans larger networks without /24 limitation) |
| `AUTO_DISCOVERY_FULL_SWEEP_MAX_HOSTS` | `65536` | Maximum number of hosts to scan in full sweep mode |

---

## 📡 API Reference

Full interactive docs at **http://localhost:8000/docs**

### Cameras

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/cameras/` | List all cameras |
| `POST` | `/api/cameras/` | Add a camera |
| `GET` | `/api/cameras/{id}` | Get a camera |
| `PATCH` | `/api/cameras/{id}` | Update a camera |
| `DELETE` | `/api/cameras/{id}` | Delete a camera |

### Events

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/events/` | List events (filterable by camera, type, class, date) |

### Alert Rules

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/alerts/` | List alert rules |
| `POST` | `/api/alerts/` | Create an alert rule |
| `PATCH` | `/api/alerts/{id}` | Update an alert rule |
| `DELETE` | `/api/alerts/{id}` | Delete an alert rule |

### Streaming

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/stream/{camera_id}` | MJPEG live stream |
| `GET` | `/snapshot/{camera_id}` | Latest JPEG frame |
| `GET` | `/snapshots/file/{filename}` | Saved snapshot file |
| `WS`  | `/ws/{camera_id}` | WebSocket binary frame stream |

---

## 🤖 AI Models

AI-Cam uses **YOLOv8** (by Ultralytics). Models are automatically downloaded on first run.

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `yolov8n.pt` | 6 MB | Fastest | Good (default) |
| `yolov8s.pt` | 22 MB | Fast | Better |
| `yolov8m.pt` | 52 MB | Medium | Even better |
| `yolov8l.pt` | 87 MB | Slower | High |
| `yolov8x.pt` | 136 MB | Slowest | Highest |

Set `YOLO_MODEL=yolov8s.pt` in `.env` to use a larger model.

---

## 📸 Adding a Camera

### USB Webcam
```
Source: 0
```
(Use `1`, `2`, etc. for additional USB cameras.)

### RTSP IP Camera
```
Source: rtsp://username:password@192.168.1.100:554/stream1
```

### HTTP MJPEG
```
Source: http://192.168.1.100:8080/video
```

### Auto-discover (LAN + USB)
- **Automatic on startup**: By default, AI-Cam automatically scans your network when it starts and finds cameras
- **Credential brute-forcing**: Tests 50+ common default credentials (admin/admin, root/root, etc.) on discovered cameras
- **Auto-add cameras**: Cameras with valid credentials are automatically added to your dashboard
- **Full IP sweep mode**: Enable `AUTO_DISCOVERY_FULL_SWEEP=true` to scan larger network ranges without the /24 subnet limitation (useful for scanning entire /16 or larger networks)
- **On-demand discovery**: In the **Cameras** page, click **Auto-discover** to manually scan local subnets and find IP cameras
- **API endpoint**: Use `POST /api/cameras/discover` with `allow_full_sweep: true` to trigger a full IP sweep programmatically
- Provide optional subnets (e.g. `192.168.1.0/24`) or leave blank to scan active interfaces
- Results can be added directly or used as a starting point for manual configuration

**Discovery methods:**
- **USB webcams**: Probes local USB indexes (0-5)
- **Credential brute-forcing**: Automatically tests 50+ common default credentials on discovered cameras
- **RTSP scanning**: Expanded port coverage (554, 8554, 10554, 7447, 88, 5000, 37777, 34567, 9000)
- **HTTP scanning**: Expanded port coverage (80, 81, 82, 85, 8000, 8080, 8081, 8888, 9000, 10000)
- **ONVIF/WS-Discovery**: Industry-standard IP camera protocol with device information retrieval
- **UPnP/mDNS/Bonjour**: Zero-configuration networking for consumer cameras and IoT devices
- **RTMP/RTMPS**: Real-Time Messaging Protocol for streaming cameras and NVRs (ports 1935, 1936, 8935)
- **WebRTC**: Modern peer-to-peer streaming protocol detection via mDNS
- **MQTT**: Home Assistant auto-discovery pattern for IoT cameras
- **SIP/VoIP**: Session Initiation Protocol for IP cameras with VoIP capabilities (ports 5060, 5061)
- **CoAP**: Constrained Application Protocol for IoT cameras (ports 5683, 5684)
- **SSDP/UPnP-AV**: Enhanced discovery for NVR/DVR systems and media servers

The enhanced discovery system can now find cameras from major manufacturers including:
- Axis, Hikvision, Dahua, Reolink, Amcrest
- Wyze, Ring, Arlo, Nest (local modes)
- Generic ONVIF-compliant cameras
- RTMP streaming servers and NVRs
- WebRTC-enabled modern cameras
- MQTT-based IoT cameras (Home Assistant compatible)
- SIP/VoIP cameras
- CoAP IoT devices
- UPnP MediaServer devices and DVR/NVR systems
- And many more...

---

## 🔑 Vendor Cloud Integrations

AI-Cam includes built-in integrations for popular cloud camera services, allowing you to access your cameras without being on the same local network.

### Zmodo Cloud (user.zmodo.com)

Access your Zmodo cameras via the cloud service at user.zmodo.com:

**Features:**
- Login with your Zmodo account email and password
- Fetches all cameras associated with your account
- Supports HD (1080p) and SD (480p) streaming quality
- FLV stream format over HTTPS
- No local network access required

**Usage:**
1. Go to the **Cameras** page
2. Click **Auto-discover**
3. Scroll to the **Zmodo Cloud login** section
4. Enter your Zmodo account credentials
5. Select stream quality (HD or SD)
6. Click **Login to Zmodo Cloud**
7. Your cameras will be discovered and can be added to your dashboard

**API endpoint:** `POST /api/cameras/zmodo/cloud/login`

### Blink Cloud

Access your Blink cameras via cloud liveview:

**Features:**
- Login with your Blink account credentials
- Supports 2FA (two-factor authentication) codes
- Supports recovery codes for backup authentication
- Fetches liveview RTSP URLs for all cameras
- Works with all Blink camera models that support liveview

**Usage:**
1. Go to the **Cameras** page
2. Click **Auto-discover**
3. Scroll to the **Blink login** section
4. Enter your Blink account email and password
5. If prompted for 2FA, enter your 6-digit code or recovery code
6. Click **Login to Blink**
7. Your cameras will be discovered and can be added to your dashboard

**API endpoint:** `POST /api/cameras/blink/login`

### Local Vendor Integrations

For cameras on your local network, AI-Cam also supports:

- **Zmodo (local)**: Direct RTSP or JPEG snapshot access to Zmodo cameras on your LAN
- **EseeCam/EseeCloud**: RTSP builder with snapshot fallback for EseeCam devices
- **Geeni/Tuya**: Local camera access and smart light control

---

## 🔔 Alert Rules Examples

**Alert on any person detection, console only:**
```json
{
  "name": "Person detected",
  "trigger_class": "person",
  "notify_via": "console"
}
```

**Alert on any detection on camera 1, send to webhook:**
```json
{
  "name": "Front door alert",
  "camera_id": 1,
  "trigger_class": "*",
  "notify_via": "webhook",
  "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
}
```

**Email alert for vehicles:**
```json
{
  "name": "Vehicle in parking lot",
  "trigger_class": "car",
  "notify_via": "email,console"
}
```

---

## 🧪 Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Coverage report:
```bash
pytest --cov=src --cov-report=html
```

---

## 🏗️ Project Structure

```
ai-cam-master/
├── src/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models/              # ORM models (Camera, Event, AlertRule)
│   ├── schemas/             # Pydantic request/response models
│   ├── camera/
│   │   ├── stream.py        # Per-camera capture + detection thread
│   │   └── manager.py       # Multi-camera orchestrator
│   ├── detection/
│   │   ├── detector.py      # YOLOv8 wrapper
│   │   └── motion.py        # MOG2 motion detector
│   ├── alerts/
│   │   └── manager.py       # Alert rule evaluation + notifications
│   ├── api/                 # FastAPI routers
│   ├── static/              # CSS, JS, images
│   └── templates/           # Jinja2 HTML templates
├── tests/                   # pytest test suite
├── run.py                   # Uvicorn entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

This software is intended for **private use** and **shareware** distribution.
You may use, modify, and redistribute freely under the terms of the MIT License.

---

## 🙏 Acknowledgements

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — AI detection
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [OpenCV](https://opencv.org/) — Video capture & processing
- Inspired by [Coram AI](https://www.coram.ai/) — commercial reference implementation
