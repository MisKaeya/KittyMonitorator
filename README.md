<div align="center">

```
██╗  ██╗██╗████████╗████████╗██╗   ██╗
██║ ██╔╝██║╚══██╔══╝╚══██╔══╝╚██╗ ██╔╝
█████╔╝ ██║   ██║      ██║    ╚████╔╝ 
██╔═██╗ ██║   ██║      ██║     ╚██╔╝  
██║  ██╗██║   ██║      ██║      ██║   
╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝      ╚═╝   

███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗  █████╗ ████████╗ ██████╗ ██████╗ 
████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗
██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝███████║   ██║   ██║   ██║██████╔╝
██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗██╔══██║   ██║   ██║   ██║██╔══██╗
██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║██║  ██║   ██║   ╚██████╔╝██║  ██║
╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
```

**A distributed IoT system for monitoring your cats' behaviour in real time.**  
*Because your cat deserves enterprise-grade infrastructure.* 🐾

---

![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Sockets](https://img.shields.io/badge/Sockets-TCP%20%2F%20UDP-00C896?style=for-the-badge)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6B6B?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Components](#-components)
- [Communication Protocol](#-communication-protocol)
- [Concurrency Model](#-concurrency-model)
- [Sensors & Behaviour Simulation](#-sensors--behaviour-simulation)
- [JSON Database](#-json-database)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Configuration](#️-configuration)
- [Actuator Rules](#-actuator-rules)
- [Known Limitations](#-known-limitations)

---

## 🐱 Overview

**KittyMonitorator** is a distributed system built for the TEC502 — Distributed Systems course. It monitors the daily behaviour of domestic cats through five virtual sensors, a central server acting as a message broker, two specialised actuators and a local GUI application.

The core design problem it solves: **high coupling**. Instead of every sensor talking directly to every actuator and the GUI — which would require O(n²) connections — all communication flows through a single server. Sensors only know the server's address. The server handles everything else.

```
Without broker (tightly coupled):          With broker (KittyMonitorator):

Sensor1 ──► Actuator1                      Sensor1 ──┐
Sensor1 ──► Actuator2                      Sensor2 ──┤
Sensor1 ──► GUI                            Sensor3 ──┼──► Server ──► Actuator1
Sensor2 ──► Actuator1                      Sensor4 ──┤             ──► Actuator2
Sensor2 ──► Actuator2          vs.         Sensor5 ──┘             ──► GUI
Sensor2 ──► GUI
...15 connections for 5 sensors            ...5 connections for 5 sensors
```

---

## 🏗 Architecture

```
                     ┌─────────────────────────────────────────────────────┐
                     │                  DOCKER NETWORK                      │
                     │                (kitty_network)                       │
                     │                                                       │
  ┌──────────────┐   │  ┌─────────────────────────────────────────────────┐│
  │   LOCAL      │   │  │              kitty_server                       ││
  │   MACHINE    │   │  │                                                  ││
  │              │   │  │  ┌──────────────┐   ┌───────────────────────┐   ││
  │  ┌────────┐  │   │  │  │  UDP Loop    │   │   Worker Pool (×10)   │   ││
  │  │CatApp  │◄─┼───┼──┼──│  :2001       │──►│   per-cat locks       │   ││
  │  │(Tkinter│  │   │  │  └──────────────┘   └──────────┬────────────┘   ││
  │  │  GUI)  │  │   │  │                                 │                ││
  │  └────────┘  │   │  │  ┌──────────────┐              │                ││
  │   TCP:2005   │   │  │  │  TCP Server  │◄─────────────┘                ││
  └──────┬───────┘   │  │  │  :2005       │                               ││
         │           │  │  └──────────────┘                               ││
         │ TCP       │  │         │ TCP (persistent connections)           ││
         │           │  └─────────┼───────────────────────────────────────┘│
         │           │            │                                          │
         │           │    ┌───────┴────────────────────┐                    │
         │           │    ▼                            ▼                    │
         │           │  ┌─────────────────┐  ┌──────────────────────┐      │
         │           │  │ atuador_access  │  │  atuador_welfare     │      │
         │           │  │   TCP :2000     │  │    TCP :2003         │      │
         │           │  │                 │  │                       │      │
         │           │  │ door   → block  │  │ bed     → alert      │      │
         │           │  │ window → block  │  │ sandbox → alert      │      │
         │           │  │ food   → block  │  │                       │      │
         │           │  └─────────────────┘  └──────────────────────┘      │
         │           │                                                       │
         │           │  ┌──────────────────────────────────────────────┐    │
         │           │  │              SENSORS  (UDP → :2001)          │    │
         │           │  │                                               │    │
         │           │  │  [🚪 door  :01]  [🪟 window :03]             │    │
         │           │  │  [🍽 food  :02]  [🛏 bed    :04]             │    │
         │           │  │  [🏖 sandbox :05]                            │    │
         │           │  │                                               │    │
         │           │  │  interval: 100ms  |  protocol: UDP/JSON-NL   │    │
         │           │  └──────────────────────────────────────────────┘    │
         │           └─────────────────────────────────────────────────────┘
         │
         └──► TCP port 2005 exposed via port mapping
```

---

## 🧩 Components

<details>
<summary><b>🖥️ Server — <code>server/server.py</code></b></summary>

<br>

The central broker. Receives UDP packets from all sensors, maintains state for each registered cat, decides when to call the actuators and forwards notifications to the GUI.

**Key responsibilities:**
- Bind UDP socket on port `2001` to receive sensor events
- Bind TCP socket on port `2005` to accept GUI connections
- Maintain two persistent TCP connections to the actuators (ports `2000` and `2003`)
- Manage per-cat state: counters, block flags, previous sensor states, event timestamps
- Run a 10-thread worker pool to process packets concurrently
- Write event logs asynchronously to JSON files

**Ports:**

| Direction | Protocol | Port | Purpose |
|-----------|----------|------|---------|
| Inbound   | UDP      | 2001 | Sensor events |
| Inbound   | TCP      | 2005 | GUI connections |
| Outbound  | TCP      | 2000 | Access actuator |
| Outbound  | TCP      | 2003 | Welfare actuator |

</details>

<details>
<summary><b>⚙️ Access Actuator — <code>server/atuator_access.py</code></b></summary>

<br>

Handles physical access and feeding rules. Listens on TCP port `2000`. Receives a sensor type and current event count from the server, applies business rules and returns an action response.

**Rules:**

| Sensor | Threshold (warn) | Threshold (block) | Action |
|--------|-----------------|-------------------|--------|
| Door   | > 5 exits       | > 10 exits        | `block_door` |
| Window | > 5 exits       | > 10 exits        | `block_window` |
| Food   | > 4 meals       | > 8 meals         | `block_dispenser` |

The actuator is **stateless** — it holds no counters. All state lives in the server.

</details>

<details>
<summary><b>💚 Welfare Actuator — <code>server/atuator_welfare.py</code></b></summary>

<br>

Monitors health and behavioural patterns. Listens on TCP port `2003`. Never blocks devices — only emits alerts and requests counter resets.

**Rules:**

| Sensor  | Threshold | Alert |
|---------|-----------|-------|
| Bed     | > 15 naps | Possible depression / sadness |
| Sandbox | > 3 uses  | Possible health issue — vet recommended |

When the owner confirms the alert in the GUI, the server resets the counter (`reset_count: true`).

</details>

<details>
<summary><b>📡 Sensors — <code>House_sensors/</code></b></summary>

<br>

Five independent Python processes, each running in its own Docker container. Each sensor:

1. Reads `cats.json` at startup to get the list of registered cats
2. Simulates events using `random.choices()` with weighted probabilities
3. Sends UDP packets to the server every `100ms`

| File | Sensor ID | Monitors | Castrated effect | Kitten effect |
|------|-----------|----------|-----------------|---------------|
| `cat_doorsensor.py`   | `01` | Door exits       | ↓ probability (0.01 → 0.00001) | — |
| `cat_foodsensor.py`   | `02` | Food dispenser   | ↑ probability (0.0001 → 0.01)  | — |
| `cat_windowsensor.py` | `03` | Window exits     | ↓ probability (0.0005 → 0.0001)| — |
| `cat_bedsensor.py`    | `04` | Bed usage        | no change                      | — |
| `cat_sanboxsensor.py` | `05` | Sandbox usage    | —                              | ↑ probability (0.0001 → 0.001) |

</details>

<details>
<summary><b>🖼️ GUI — <code>interface/CatApp.py</code></b></summary>

<br>

A Tkinter desktop application that runs **outside Docker** on the operator's machine. Connects to the server via TCP on port `2005`.

**Features:**
- Register, view, edit and delete cat profiles (stored in `cats.json`)
- Real-time sensor dashboard with per-sensor event feed and animated pulse indicator
- Manual controls: lock/unlock door, window and food dispenser per cat
- Toast notification system (info / warn / critical) — critical toasts require owner confirmation
- Animated pixel-art mascot that follows the cursor

**Threading model:**  
A daemon thread listens for server messages. When an alert arrives, it calls `root.after(0, handler)` to schedule the UI update on Tkinter's main thread — the only thread allowed to modify the interface.

</details>

---

## 📡 Communication Protocol

All components communicate using **JSON-NL** (newline-delimited JSON): each message is a UTF-8 encoded JSON object followed by `\n`. This allows multiplexing multiple messages over a single TCP stream without a length header.

<details>
<summary><b>Sensor → Server  (UDP)</b></summary>

<br>

```json
{
  "sensorID":      "01",
  "cat_name":      "luna",
  "timestamp":     "2025-04-05 14:23:01",
  "cat_state":     true,
  "door_msg":      "movement detected.",
  "door_hangouts": 3
}
```

| Field | Description |
|-------|-------------|
| `sensorID` | Sensor type identifier (`01`–`05`) |
| `cat_name` | Name of the cat associated with the event |
| `timestamp` | Local datetime of the reading |
| `cat_state` | `true` = event active, `false` = event ended |
| `*_msg` | Human-readable status string |
| `*_count` | Local counter accumulated in the sensor process |

</details>

<details>
<summary><b>Server → Actuator  (TCP request)</b></summary>

<br>

```json
{
  "sensor_type": "door",
  "params": {
    "count":    6,
    "cat_name": "luna"
  }
}
```

| Field | Description |
|-------|-------------|
| `sensor_type` | Which sensor triggered the call |
| `params.count` | Current daily event count (maintained by the server) |
| `params.cat_name` | Cat name — used by the actuator to personalise the alert message |

</details>

<details>
<summary><b>Actuator → Server  (TCP response)</b></summary>

<br>

```json
{
  "sensor":      "door",
  "cat_name":    "luna",
  "timestamp":   "2025-04-05T14:23:01.123456",
  "action":      null,
  "message":     "⚠️ luna has already gone out 6 times today.",
  "reset_count": false,
  "needs_owner": false
}
```

| Field | Description |
|-------|-------------|
| `action` | `block_door` / `block_window` / `block_dispenser` / `null` |
| `message` | Alert text forwarded to the GUI. `null` = no notification |
| `reset_count` | `true` = server must zero the counter after owner confirmation |
| `needs_owner` | `true` = GUI must display a sticky critical toast |

</details>

<details>
<summary><b>Server → GUI  (TCP alert)</b></summary>

<br>

```json
{
  "sensor":      "door",
  "cat_name":    "luna",
  "message":     "🚨 luna went out 11 times! Door blocked.",
  "action":      "block_door",
  "subtle":      false,
  "needs_owner": true,
  "estado":      "aventureiro",
  "timestamp":   "2025-04-05T14:23:01.123456",
  "type":        null
}
```

| Field | Description |
|-------|-------------|
| `sensor` | Which sensor feed to append the event to in the GUI |
| `action` | If present, triggers a visual control change in the dashboard |
| `subtle` | `true` = info toast (auto-hides); `false` = warning toast |
| `needs_owner` | `true` = critical toast, stays until owner presses OK |
| `estado` | New behavioural state of the cat (`dormindo` / `comendo` / `aventureiro` / `gordo`) |
| `type` | `"state_update"` = silent state change only, no toast displayed |

</details>

<details>
<summary><b>GUI → Server  (TCP command)</b></summary>

<br>

```json
{ "command": "open_door", "cat": "luna" }
```

| Command | Effect |
|---------|--------|
| `open_door` | Unblocks door, resets door counter |
| `close_door` | Manually blocks door |
| `open_window` | Unblocks window, resets window counter |
| `close_window` | Manually blocks window |
| `unblock_food` | Unblocks dispenser, resets food counter |
| `block_food` | Manually blocks dispenser |
| `ok_bed` | Owner confirmed bed alert — resets bed counter |
| `ok_sandbox` | Owner confirmed sandbox alert — resets sandbox counter |

</details>

---

## ⚙️ Concurrency Model

The server uses a **three-level concurrency architecture** to handle high-frequency sensor data without blocking or race conditions.

```
┌─────────────────────────────────────────────────────────────────┐
│  LEVEL 1 — UDP Reception  (main thread, never blocked by logic) │
│                                                                   │
│  sensor_sock.recvfrom()                                          │
│       │                                                          │
│       ▼                                                          │
│  _packet_queue.put_nowait()  ◄── max 2000 items                 │
│       │                                                          │
│       └── if full: silently discard (no blocking)               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LEVEL 2 — Concurrent Processing  (10 worker threads)           │
│                                                                   │
│  _packet_queue.get()                                             │
│       │                                                          │
│       ▼                                                          │
│  _get_cat_lock(cat_name)  ◄── per-entity lock                   │
│       │                                                          │
│       │  ✓ Different cats → processed in parallel               │
│       │  ✓ Same cat       → serialised (no race conditions)     │
│       │                                                          │
│       ▼                                                          │
│  _process_packet()                                               │
│    ├── state transition check  (False → True only)              │
│    ├── MIN_EVENT_INTERVAL check  (debounce)                     │
│    ├── actuator TCP call  (persistent connection)               │
│    └── send_interface_alert()                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LEVEL 3 — Async Log Writing  (1 dedicated daemon thread)       │
│                                                                   │
│  _log_queue.get()  ◄── max 500 items                            │
│       │                                                          │
│       ▼                                                          │
│  json.dump() → JSON file  (max 500 records, auto-rotated)       │
└─────────────────────────────────────────────────────────────────┘
```

**Why per-entity locks instead of a single global lock?**

A global lock would serialise *all* events across *all* cats. Per-entity locks allow full parallelism between different cats while preventing the race condition where two workers read the same counter simultaneously and both write the same incremented value — losing one increment.

**Why MIN_EVENT_INTERVAL?**

Sensors emit every 100ms. A physical event (e.g. the cat sitting on the bed for 30 minutes) produces ~18,000 packets. Without debouncing that is 18,000 counted events. `MIN_EVENT_INTERVAL` ensures only one count per physical event by ignoring subsequent `True` readings within the minimum duration window per sensor.

---

## 🐾 Sensors & Behaviour Simulation

Each sensor uses `random.choices()` with two outcomes: `[True, False]` with configured weights. The cat's profile modifies the weights to simulate realistic behaviour differences.

```
                    EVENT PROBABILITY MAP
    ┌─────────────┬────────────┬───────────────────────────────┐
    │   Sensor    │  Default   │  Modified Profile             │
    ├─────────────┼────────────┼───────────────────────────────┤
    │ 🚪 Door     │ 1.0%       │ 0.001%  ← castrated           │
    │ 🪟 Window   │ 0.05%      │ 0.01%   ← castrated           │
    │ 🍽 Food     │ 0.01%      │ 1.0%    ← castrated           │
    │ 🏖 Sandbox  │ 0.01%      │ 0.1%    ← kitten              │
    │ 🛏 Bed      │ 0.1%       │ (no change)                   │
    └─────────────┴────────────┴───────────────────────────────┘

    Rationale:
    • Castrated cats are less territorial  → fewer door/window exits
    • Castrated cats are more sedentary    → higher food usage
    • Kittens have immature digestion      → more sandbox usage
```

**Sleep Logic:** When the bed sensor detects the cat is sleeping (`bed_occupied = True`), all events from door, window and food sensors are discarded as physically impossible noise. Bed and sandbox sensors always process regardless of sleep state.

---

## 🗄️ JSON Database

Because a relational database was out of scope, persistence is handled by **7 JSON files** maintained by the server's async log worker. Each file acts as a table with a maximum of 500 records (auto-rotated).

```
interface/
└── cats.json                  ← Cat registry (shared via Docker volume)
    {
      "luna": {
        "raça": "siamês",      "pelagem": "cinza",
        "peso": 4.2,           "idade": 3,
        "filhote": false,      "castrado": true,
        "estado": "dormindo",  "foto": "photos/cat_1234.jpg"
      }
    }

server/logs/
├── cat_activity.json          ← Total event counts per cat per sensor
│   { "luna": { "door": 3, "window": 0, "food": 7, "bed": 2, "sandbox": 1 } }
│
├── door_monitorator.json      ← [{ cat_name, timestamp, cat_state, total_exits, blocked }]
├── window_monitorator.json    ← [{ cat_name, timestamp, cat_state, total_exits, blocked }]
├── dispenser_monitorator.json ← [{ cat_name, timestamp, cat_state, total_meals, blocked }]
├── bed_monitorator.json       ← [{ cat_name, timestamp, cat_state, total_naps, bed_occupied }]
└── sandbox_monitorator.json   ← [{ cat_name, timestamp, cat_state, total_usage }]
```

> ⚠️ `cats.json` is mounted as a Docker volume shared between the GUI and all sensor containers. Sensors load it **once at startup** — restart sensor containers after registering new cats.

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Python 3.10+ with Tkinter *(for the GUI, runs locally)*
- Optional: `pip install Pillow` *(enables cat profile photos in the GUI)*

### 1. Clone the repository

```bash
git clone https://github.com/your-username/KittyMonitorator.git
cd KittyMonitorator
```

### 2. Register at least one cat

Before starting the containers, open the GUI **or** manually edit `interface/cats.json`:

```json
{
  "luna": {
    "raça": "siamês",
    "pelagem": "cinza",
    "peso": 4.2,
    "idade": 3,
    "filhote": false,
    "castrado": true,
    "estado": "dormindo",
    "foto": ""
  }
}
```

> **Why first?** Sensors load `cats.json` at startup. An empty file means no events will be generated until containers are restarted.

### 3. Start the Docker stack

```bash
docker-compose up --build
```

Expected output:
```
[SERVER] UDP sensors         → 0.0.0.0:2001
[SERVER] TCP interface       → 0.0.0.0:2005
[SERVER] TCP access actuator → kitty_atuador_access:2000
[SERVER] TCP welfare actuator→ kitty_atuador_welfare:2003
[SERVER] Pool of 10 workers started for packet processing
[ATUADOR-ACESSO]  Escutando em 0.0.0.0:2000
[ATUADOR-WELFARE] Escutando em 0.0.0.0:2003
```

### 4. Launch the GUI

In a **separate terminal** on your local machine:

```bash
python interface/CatApp.py
```

The GUI connects to `127.0.0.1:2005` automatically. You should see in the server logs:

```
[SERVER] Interface connected: ('172.17.0.1', 52341)
```

### 5. Watch the dashboard

Navigate to **📡 painel de sensores**, select a cat and watch events arrive in real time.

### Stopping

```bash
docker-compose down --remove-orphans
```

### Rebuilding after code changes

```bash
docker-compose down --remove-orphans && docker-compose up --build
```

---

## 📁 Project Structure

```
KittyMonitorator/
│
├── docker-compose.yml              # Orchestrates all 9 containers
│
├── dockerFiles/
│   ├── Dockerfile.server           # python:3.10-slim + server/
│   ├── Dockerfile.atuador_access   # python:3.10-slim + server/
│   ├── Dockerfile.atuador_welfare  # python:3.10-slim + server/
│   └── Dockerfile.sensor           # python:3.10-slim + House_sensors/
│
├── server/
│   ├── server.py                   # Central broker (UDP:2001, TCP:2005)
│   ├── atuator_access.py           # Access actuator  (TCP:2000)
│   ├── atuator_welfare.py          # Welfare actuator (TCP:2003)
│   └── logs/                       # JSON database (auto-created at runtime)
│       ├── cat_activity.json
│       ├── door_monitorator.json
│       ├── window_monitorator.json
│       ├── dispenser_monitorator.json
│       ├── bed_monitorator.json
│       └── sandbox_monitorator.json
│
├── House_sensors/
│   ├── cat_doorsensor.py           # sensorID: 01 | UDP | 100ms
│   ├── cat_foodsensor.py           # sensorID: 02 | UDP | 100ms
│   ├── cat_windowsensor.py         # sensorID: 03 | UDP | 100ms
│   ├── cat_bedsensor.py            # sensorID: 04 | UDP | 100ms
│   └── cat_sanboxsensor.py         # sensorID: 05 | UDP | 100ms
│
├── interface/
│   ├── CatApp.py                   # Tkinter GUI (runs locally, NOT in Docker)
│   ├── cats.json                   # Cat registry (shared volume with sensors)
│   └── photos/                     # Cat profile photos (optional)
│
└── test_server.py                  # Log directory monitor / basic test script
```

---

## ⚙️ Configuration

All configuration is handled via **environment variables** in `docker-compose.yml`. No hardcoded addresses in source code.

| Variable | Default | Used by | Description |
|----------|---------|---------|-------------|
| `BIND_HOST` | `0.0.0.0` | server | Interface to bind UDP/TCP sockets |
| `APP_PORT` | `2005` | server | TCP port for GUI connections |
| `SENSOR_PORT` | `2001` | server | UDP port for sensor data |
| `ATUATOR_ACCESS_HOST` | `kitty_atuador_access` | server | Hostname of the access actuator |
| `ATUATOR_ACCESS_PORT` | `2000` | server | TCP port of the access actuator |
| `ATUATOR_WELFARE_HOST` | `kitty_atuador_welfare` | server | Hostname of the welfare actuator |
| `ATUATOR_WELFARE_PORT` | `2003` | server | TCP port of the welfare actuator |
| `SERVER_HOST` | `kitty_server` | sensors | Hostname of the server (UDP destination) |

> **Note:** Ports below 1024 are reserved for the OS superuser on Linux. All ports in this project are deliberately set above 1024 to avoid permission errors inside Docker containers.

---

## 🔔 Actuator Rules

<details>
<summary><b>Access Actuator — door, window, food</b></summary>

<br>

```
DOOR / WINDOW
─────────────────────────────────────────────
count >  5  →  ⚠️  Warning alert to GUI
count > 10  →  🚨  Block device + critical toast (owner must confirm)
              server sets *_blocked = True, resets counter to 0

FOOD DISPENSER
─────────────────────────────────────────────
count >  4  →  ⚠️  Warning: eating more than usual
count >  8  →  🚨  Block dispenser + critical toast
              server sets food_blocked = True, resets counter to 0

While blocked:
  → sensor keeps detecting attempts
  → SUBTLE_THROTTLE: max one alert per 15 seconds (no flooding)
  → owner unlocks via GUI controls
```

</details>

<details>
<summary><b>Welfare Actuator — bed, sandbox</b></summary>

<br>

```
BED
─────────────────────────────────────────────
count > 15  →  😿  Alert: possible depression / sadness
              reset_count = True (server zeros after owner confirms)
              device is NOT blockable

SANDBOX
─────────────────────────────────────────────
count >  3  →  🏥  Alert: possible health issue — see a vet
              reset_count = True
              device is NOT blockable
```

</details>

---

## ⚠️ Known Limitations

<details>
<summary><b>No dynamic cat reloading</b></summary>

<br>

Sensors load `cats.json` **once at startup**. Cats registered after the containers start will not appear in sensor events until sensor containers are restarted.

```bash
docker-compose restart sensor_bed sensor_door sensor_food sensor_sandbox sensor_window
```

</details>

<details>
<summary><b>No sensor heartbeat / failure detection</b></summary>

<br>

UDP has no connection state. If a sensor container crashes, the server is not notified — the event feed simply stops updating. No automatic reconnection or alerting is implemented for sensor failures.

</details>

<details>
<summary><b>Recommended cat limit: ~20</b></summary>

<br>

The system was tested with **2 cats**. Performance degrades as the number grows because sensors select cat names randomly on every packet — with many cats, the event frequency per individual cat drops and actuator thresholds become much harder to reach. Each additional cat also creates a new lock object in the server's memory.

</details>

<details>
<summary><b>GUI must run outside Docker</b></summary>

<br>

Tkinter requires a display server (X11 / Wayland / Quartz / GDI). Running it inside a headless Docker container requires additional X11 forwarding configuration which is not set up in this project. The GUI connects to `127.0.0.1:2005` via the server's exposed port mapping.

</details>

---

<div align="center">

Made with 🐾 and way too many threads.

*This system does not replace attentive care for your cat.*

</div>
