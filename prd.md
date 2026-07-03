# Product Requirement Document (PRD)

## Project Name: SafeSite-Edge Pro – Complete Safety Suite

**Team Name:** Quantix

**Target Event:** Tata Technologies InnoVent Hackathon

**Track:** Edge AI for Operator Safety & Human–Machine Interaction

**Document Date:** June 2026

---

## 1. Executive Summary & Vision

**SafeSite-Edge Pro** is a **decentralized, on‑machine Edge AI safety ecosystem** that transforms any heavy machine into an intelligent, self‑contained safety co‑pilot.

Unlike reactive single‑function systems, SafeSite‑Edge Pro fuses **six real‑time hazard detection layers** – operator fatigue, blind‑spot intrusion, PPE compliance, acoustic anomalies, emergency gestures, and an offline natural‑language safety assistant – all running simultaneously on a **single edge node (<6 GB VRAM)** with **zero internet dependency**.

By deploying this suite, industrial sites eliminate the need for multiple proprietary black boxes, reduce accident response latency from minutes to milliseconds, and give operators instant, conversational access to thousands of pages of safety manuals – even in the deepest mines or most remote construction zones.

---

## 2. System Architecture (Optimized for Single‑Pass Inference)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE HARDWARE (Laptop / Jetson / x86)          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CENTRAL ORCHESTRATOR (FastAPI)                    │   │
│  │  - Loads all quantized models once at boot                          │   │
│  │  - Manages MQTT event bus & WebSocket bridge                        │   │
│  │  - Routes queries to RAG engine                                     │   │
│  │  - Publishes actuation commands to MQTT broker                      │   │
│  └───────────────┬─────────────┬─────────────┬─────────────┬───────────┘   │
│                  │             │             │             │               │
│  ┌───────────────▼─────┐ ┌─────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐       │
│  │   UNIFIED YOLOv10   │ │Cabin Guard│ │ Acoustic   │ │   RAG      │       │
│  │   (PPE + Perimeter  │ │ (Face Mesh│ │ Anomaly    │ │  Engine    │       │
│  │    + Machinery)     │ │  + GRU)   │ │ (YAMNet)   │ │(Chroma+LLM)│       │
│  └───────────┬─────────┘ └─────┬─────┘ └──────┬─────┘ └──────┬──────┘       │
│              │                   │              │               │           │
│              └───────────────────┼──────────────┼───────────────┘           │
│                                  │              │                           │
│                          ┌───────▼──────────────▼───────┐                   │
│                          │      LOCAL MQTT BROKER       │                   │
│                          │        (Mosquitto)           │                   │
│                          └───────────────┬───────────────┘                   │
│                                          │                                   │
│                              ┌───────────▼───────────┐                       │
│                              │  WebSocket Proxy      │                       │
│                              │  (MQTT → WS bridge)   │                       │
│                              └───────────┬───────────┘                       │
└──────────────────────────────────────────┼───────────────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    │ (WebSocket)          │ (MQTT)               │ (MQTT)
                    ▼                      ▼                      ▼
          ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
          │ REACT DASHBOARD │   │   ESP32 NODE    │   │   ESP32 NODE    │
          │ - Real‑time     │   │   - 4‑Channel   │   │   - Strobe      │
          │   alerts        │   │     Relay       │   │     Light       │
          │ - RAG chatbot   │   │   - Throttle    │   │   - Siren       │
          │ - Event log     │   │     Grounding   │   │                 │
          └─────────────────┘   └─────────────────┘   └─────────────────┘
```

**Key Optimizations (as requested):**
- **Unified YOLO model** – one inference pass detects `person_with_ppe`, `person_no_ppe`, `machinery`, `hazard`. No interleaving, no weight swapping.
- **Conditional gesture activation** – MediaPipe Hands runs only when a person is detected inside a boundary zone (from YOLO) OR when the machine is in motion.
- **MQTT → WebSocket bridge** – Your React dashboard subscribes to a single WebSocket endpoint; no browser MQTT plugins needed.
- **Hardware actuation layer** – ESP32 nodes subscribe to MQTT topics and execute physical interventions (relay switching, strobe activation) with <25 ms latency.

---

## 3. Core Modules – Detailed Functional Requirements

### Module 1: Cabin Guardian (Operator Fatigue & Distraction)
- **Input:** Internal IR camera (cabin‑facing)
- **Processing:** MediaPipe Face Mesh → extract Eye Aspect Ratio (EAR) & Mouth Aspect Ratio (MAR) over a rolling 30‑frame window → feed into a **2‑layer GRU** (trained on drowsiness patterns)
- **Output (MQTT topic):** `cabin/fatigue` – `{ "level": 0.0–1.0, "distracted": bool, "eyes_closed_sec": float }`
- **Latency:** <10 ms per frame on CPU

### Module 2+3: Unified Perimeter & PPE Sentinel
> *Optimization applied: single YOLOv10 model detects all external risks in one pass*

- **Input:** External wide‑angle camera (blind‑spot / surrounding area)
- **Unified YOLOv10‑Nano** (fine‑tuned on custom dataset with 4 classes):
  - `person_with_ppe` (helmet + vest + gloves – all present)
  - `person_no_ppe` (at least one missing)
  - `machinery` (other vehicles, moving parts)
  - `hazard` (open pit, hanging cable, etc.)
- **Plus monocular distance estimation** (assuming known camera height & focal length) → approximate distance to each detected person.
- **Output (MQTT):** `perimeter/alert` – `{ "class": "person_no_ppe", "distance_m": 4.2, "missing_ppe": ["helmet"], "bbox": [x1,y1,x2,y2] }`
- **Frame rate:** 30 FPS on GPU, using <1.2 GB VRAM (INT8 quantized)

### Module 4: Acoustic Anomaly Detector
- **Input:** On‑device microphone (or simulated audio file during demo)
- **Processing:** YAMNet (quantized to INT8) running in a separate CPU thread, analyzing 2‑second windows with 1‑second overlap.
- **Anomaly classes (subset of ESC‑50):** `scream`, `glass_break`, `metal_grind`, `explosion`, `shout`
- **Output (MQTT):** `audio/anomaly` – `{ "class": "metal_grind", "confidence": 0.92, "timestamp": ... }`
- **Memory:** ~200 MB RAM, no GPU needed

### Module 5: Gesture Emergency Stop & ESP32 Actuation
> *Optimization applied: runs only when YOLO detects a person inside a 5m boundary zone OR machine is active (from CAN/telemetry)*

- **Input:** External camera (same as Module 2+3) – but only every 5th frame to save CPU.
- **Pipeline:** MediaPipe Hands → 21 keypoints per hand → LSTM (2 layers, 64 units) trained on 3 gesture sequences.
- **Gestures recognized:**
  - `STOP` (palm facing camera)
  - `HELP` (waving hand overhead)
  - `EMERGENCY_STOP` (crossed arms)
- **Output (MQTT):** `gesture/trigger` – `{ "gesture": "EMERGENCY_STOP", "confidence": 0.97, "boundary_distance": 3.1 }`
- **Physical Actuation Layer:** When a hazard or `EMERGENCY_STOP` sequence is confirmed, the central FastAPI orchestrator publishes a JSON event to the localized Eclipse Mosquitto MQTT broker. A physical ESP32 microcontroller subscribed to the broker instantly trips a 4-channel optically isolated relay board to ground the machine's throttle signal wire and activate an audio-visual strobe light within **25 ms**.
- **Fallback:** If no person in boundary zone, gesture module sleeps – zero CPU waste.

### Module 6: Offline RAG Assistant (Safety Q&A + Error Code Lookup)
- **Ingestion pipeline (pre‑hackathon):** Scrape 3–5 PDFs (e.g., Tata Safety Handbook, OSHA heavy machinery, JCB maintenance manual) using `unstructured` + `BeautifulSoup`. Chunk into 512‑token segments with 50‑token overlap.
- **Vector store:** ChromaDB with `all-MiniLM-L6-v2` embeddings (~90 MB).
- **LLM:** Phi‑3‑mini‑4k‑instruct (quantized to INT4 via Ollama / llama.cpp). Runs on GPU+CPU hybrid (offload 20 layers to GPU).
- **Query endpoint (HTTP POST):** `/query` – accepts `{ "question": "What is the procedure for hydraulic overheating?" }` – returns `{ "answer": "...", "sources": [{"page": 42, "pdf": "Tata_Hydraulics.pdf"}] }`
- **Latency:** Vector retrieval <150 ms, generation >15 tokens/sec.

---

## 4. Complete Technical Stack (Exact Frameworks)

| Component | Technology | Version / Model | Quantization | Memory |
|-----------|------------|----------------|--------------|--------|
| **Unified Object Detection** | YOLOv10‑Nano (Ultralytics) | Custom fine‑tuned | INT8 (ONNX Runtime) | 1.2 GB VRAM |
| **Face Mesh & GRU Fatigue** | MediaPipe + PyTorch | MediaPipe 0.10 + custom GRU | FP32 (CPU) | 400 MB RAM |
| **Acoustic Anomaly** | YAMNet (TensorFlow Lite) | Mobilenet‑v1 based | INT8 TFLite | 200 MB RAM |
| **Gesture LSTM** | MediaPipe Hands + TensorFlow | Custom trained | FP32 (CPU) | 150 MB RAM (conditional) |
| **Embeddings** | Sentence‑Transformers | `all-MiniLM-L6-v2` | FP16 | 90 MB RAM |
| **Vector DB** | ChromaDB | 0.5.0 | Persistent on disk | ~500 MB disk |
| **LLM Inference** | Ollama + llama.cpp | Phi‑3‑mini‑4k‑instruct‑q4 | INT4 (GGUF) | 3.2 GB VRAM+RAM |
| **Orchestration** | FastAPI | 0.115 | – | – |
| **Message Bus** | Mosquitto MQTT | 2.0 | – | – |
| **WebSocket Bridge** | `websockets` + `mqtt‑asyncio` | Custom | – | – |
| **Containerization** | Docker + docker‑compose | Latest | – | – |
| **ESP32 Firmware** | Arduino / ESP‑IDF | Custom | – | 4 MB Flash |

**Total peak VRAM:** <5.5 GB (fits in a typical laptop RTX 3060 / 6 GB)

---

## 5. Non‑Functional Requirements (NFRs)

| Metric | Target | Verification |
|--------|--------|---------------|
| **Inference latency (Unified YOLO)** | ≤25 ms/frame | Time from frame capture to MQTT alert |
| **RAG retrieval** | ≤150 ms | ChromaDB query time |
| **LLM generation** | ≥15 tokens/sec | On Intel i7 + RTX 3060 |
| **Cold start time** | ≤30 sec | Docker compose up → all models loaded |
| **Network autonomy** | 100% air‑gapped | Unplug Ethernet/WiFi; system runs |
| **CPU usage (idle)** | <20% | When no camera input |
| **Event loss** | 0% | All detections published to MQTT |
| **Dashboard data lag** | ≤100 ms | WebSocket to React update |
| **Hardware actuation latency** | ≤25 ms | MQTT publish → ESP32 relay trigger |
| **ESP32 uptime** | 99.99% | Continuous operation with watchdog timer |

---

## 6. Deployment Plan (One‑Command Hackathon Ready)

### 6.1 Pre‑Hackathon Preparation (Day -1)
1. **Scrape & chunk** the 3 source PDFs – save `chroma_db/` folder.
2. **Fine‑tune YOLOv10** on a combined PPE + machinery dataset (use Roboflow public datasets). Export to ONNX INT8.
3. **Train gesture LSTM** using your own webcam (15 min recording) or a synthetic generator.
4. **Package everything** into a Docker image with model weights baked in.
5. **Flash ESP32 nodes** with MQTT subscriber firmware and relay control logic.

### 6.2 Runtime (Day of Hackathon)
```bash
git clone https://github.com/your-team/safesite-edge-pro
cd safesite-edge-pro
docker-compose up --build
```
- After `docker-compose up`, the orchestrator:
  - Loads all models into memory.
  - Starts camera capture (or loops demo video).
  - Exposes:
    - WebSocket at `ws://localhost:8765` (for React dashboard)
    - RAG HTTP endpoint at `http://localhost:8000/query`
  - ESP32 nodes automatically connect to MQTT broker and listen for actuation commands.

### 6.3 Dashboard Integration (Your React App)
- Connect to `ws://localhost:8765` – you will receive a JSON event every time any module triggers:
  ```json
  {
    "type": "perimeter_alert",
    "data": { "class": "person_no_ppe", "distance_m": 4.2 },
    "timestamp": "2026-06-13T10:32:17Z"
  }
  ```
- For RAG queries: `POST http://localhost:8000/query` with `{ "question": "..." }`

---

## 7. Deliverables for Judges (Virtual + Live)

### 7.1 GitHub Repository Structure
```
safesite-edge-pro/
├── docker-compose.yml
├── Dockerfile.orchestrator
├── modules/
│   ├── unified_yolo.py          # Loads ONNX, runs inference
│   ├── cabin_guardian.py        # MediaPipe + GRU
│   ├── acoustic_analyzer.py     # YAMNet loop
│   ├── gesture_stop.py          # Conditional activation logic
│   └── rag_engine.py            # ChromaDB + Ollama wrapper
├── hardware/
│   ├── esp32_firmware/
│   │   ├── mqtt_relay_controller.ino
│   │   └── strobe_controller.ino
│   └── wiring_diagrams/
│       └── relay_connection.pdf
├── models/
│   ├── yolov10n_ppe_perimeter.onnx   # INT8 quantized
│   ├── gesture_lstm.h5
│   └── phi3_mini_q4.gguf
├── data/
│   ├── chroma_db/               # Pre‑computed vector store
│   └── sample_pdfs/
├── demo_assets/
│   ├── fatigue_loop.mp4
│   ├── ppe_violation.jpg
│   └── metal_grind.wav
├── scripts/
│   ├── scrape_pdfs.py
│   └── fine_tune_yolo.ipynb
└── README.md                    # Includes performance table & offline demo instructions
```

### 7.2 Submission Video Walkthrough (10 minutes max)
- **0:00–2:30 [The Pitch]:** Present the engineered concept, deep-pit constraints, and 6-layer architecture using the slide deck.
- **2:30–4:30 [Proof of Architecture]:** Transition to a local VS Code session showing a completely structured repository, an offline docker-compose orchestration file, and mock telemetry JSON payloads to verify edge data-stream formats.
- **4:30–6:30 [The Roadmap]:** Outline the concrete execution phases for Stage 2 physical hardware-in-the-loop validation using embedded nodes and CAN bus interfaces.

### 7.3 Core Pitch Deck Structure (8 Required Slides)
1. **Slide 1:** Title & Introduction (Project Identity & Track)
2. **Slide 2:** The Core Industrial Problem (Mining blind spots & signal blackouts)
3. **Slide 3:** Objective & Core Approach (Transitioning to millisecond physical intervention)
4. **Slide 4:** Solution Overview & System Architecture (The 6 edge processing modules)
5. **Slide 5:** Technical Implementation & Single-Pass Optimization (Exact quantization & VRAM metrics)
6. **Slide 6:** Hardware-in-the-Loop IoT Integration (ESP32 relay wiring configurations)
7. **Slide 7:** Quantifiable Impact & Non-Functional Results (NFR acceptance criteria matrix)
8. **Slide 8:** Project Roadmap & Future Enhancements (Stage 2 ruggedization & functional safety certification)

---

## 8. Optimization Justifications (For Q&A with Judges)

| Judge's Concern | Our Answer |
|----------------|------------|
| *"Running YOLO twice (PPE + perimeter) would be too slow."* | We fine‑tuned a **single unified YOLOv10** model that detects PPE status and perimeter hazards in **one pass**. No interleaving, no frame drop. |
| *"MediaPipe Hands always running will kill the CPU."* | Gesture module **activates only when a person is inside a 5m boundary zone** (from YOLO) OR the machine is moving. Otherwise it sleeps – near zero overhead. |
| *"How does the dashboard get data without plugins?"* | We built a **WebSocket bridge** that translates internal MQTT messages into clean JSON over WS. Your React app just uses standard `WebSocket` API. |
| *"Can you really run an LLM + CV on a laptop?"* | Yes – Phi‑3‑mini quantized to INT4 uses <3.5 GB, YOLO INT8 uses 1.2 GB, and `llama.cpp` offloads layers to GPU while YOLO runs concurrently. |
| *"How do you guarantee physical actuation in remote mines?"* | ESP32 nodes connect via **local MQTT broker** with zero cloud dependency. Relay contacts directly interface with machine safety circuits. Redundant watchdog timers ensure fail-safe behavior. |
| *"What about mining network blackouts?"* | The entire system is **fully air‑gapped**. No internet, no cellular, no satellite required. All communication is local Ethernet/WiFi between the edge node and ESP32 actuators. |

---

## 9. Acceptance Criteria (For Hackathon Judging)

- [ ] All six modules produce MQTT events when simulated inputs are provided.
- [ ] The system runs with Wi‑Fi and Ethernet physically disconnected.
- [ ] RAG answers include a page number citation from the scraped PDF.
- [ ] Unified YOLO detects `person_no_ppe` and `person_with_ppe` in the same frame.
- [ ] Gesture stop triggers **only** when a person is inside the boundary zone (demonstrate by moving out of zone → no trigger).
- [ ] The WebSocket bridge delivers at least 10 events/second to a test client.
- [ ] Total memory usage (VRAM + RAM) <6 GB as shown by `nvidia-smi` and `free -h`.
- [ ] ESP32 relay triggers within 30 ms of MQTT publish (demonstrate with oscilloscope or logic analyzer).
- [ ] Hardware actuation can be manually overridden via physical emergency stop button (fail-safe).

---

## 10. Appendix – Sample Event JSON (For React Dashboard Developer)

```json
// Fatigue event
{ "type": "fatigue", "data": { "level": 0.78, "distracted": false }, "timestamp": "..." }

// Unified YOLO event (PPE + perimeter)
{ "type": "perimeter", "data": { "class": "person_no_ppe", "distance_m": 3.2, "missing": ["helmet"] }, "timestamp": "..." }

// Acoustic anomaly
{ "type": "audio", "data": { "class": "metal_grind", "confidence": 0.94 }, "timestamp": "..." }

// Gesture trigger
{ "type": "gesture", "data": { "gesture": "EMERGENCY_STOP", "confidence": 0.98 }, "timestamp": "..." }

// RAG query response (HTTP, not WS)
{ "answer": "Immediately stop the engine and wait 15 minutes. (Page 42, Tata Hydraulics Manual)", "sources": [...] }

// Actuation command (published to MQTT, consumed by ESP32)
{ "type": "actuation", "data": { "command": "EMERGENCY_STOP", "relay_channel": 1, "duration_sec": 5 }, "timestamp": "..." }

// ESP32 status heartbeat
{ "type": "heartbeat", "data": { "node_id": "esp32_relay_01", "status": "online", "relay_state": "open" }, "timestamp": "..." }
```

---

## 11. Hardware Integration Details (ESP32 Actuation Layer)

### 11.1 ESP32 Relay Controller Wiring
```
┌─────────────────────────────────────────────────────────────────┐
│                        ESP32 DEV BOARD                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  GPIO 16 ──────► Relay 1 (Throttle Signal Ground)     │  │
│  │  GPIO 17 ──────► Relay 2 (Strobe Light)               │  │
│  │  GPIO 18 ──────► Relay 3 (Siren)                      │  │
│  │  GPIO 19 ──────► Relay 4 (Spare – Brake Actuation)    │  │
│  │  GND ──────────► Relay Common Ground                  │  │
│  │  3.3V ─────────► Relay VCC (via optoisolator)         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│         ┌────────────────────┼────────────────────┐           │
│         │                    │                    │           │
│         ▼                    ▼                    ▼           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   Relay 1   │    │   Relay 2   │    │   Relay 3   │       │
│  │ (Throttle)  │    │  (Strobe)   │    │  (Siren)    │       │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│         │                  │                  │               │
│         ▼                  ▼                  ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │  Throttle   │    │ 24V Strobe  │    │ 24V Siren   │       │
│  │  Signal     │    │  Light      │    │  Module     │       │
│  │  Grounding  │    │             │    │             │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 ESP32 Firmware Requirements
- **MQTT Client:** PubSubClient library, connecting to `mqtt://localhost:1883`
- **Subscribed Topics:**
  - `actuation/emergency_stop` – triggers relay 1 (throttle kill)
  - `actuation/warning_strobe` – triggers relays 2 & 3 (visual + audible alert)
  - `actuation/reset` – releases all relays (manual override)
- **Heartbeat:** Publishes status to `esp32/heartbeat` every 2 seconds
- **Watchdog Timer:** Resets ESP32 if no MQTT message received for 30 seconds (fail-safe)

### 11.3 Safety Circuit Design
- **Optically Isolated Relays:** 5V DC control, 10A 250V AC / 30V DC contacts
- **Normally Closed (NC) Configuration:** Throttle signal passes through NC contacts → relay opens on emergency stop (fails safe)
- **Manual Override:** Physical push-button switch connected to ESP32 GPIO with interrupt → forces relay release
- **Grounding Strategy:** Relay contacts directly short throttle signal wire to machine ground (proven kill method in mining equipment)

---

## 12. Updated Deliverables Checklist

### 12.1 Virtual Submission Package
- [ ] GitHub repository with complete source code
- [ ] 10-minute video walkthrough (as described in Section 7.2)
- [ ] 8-slide PowerPoint deck (as described in Section 7.3)
- [ ] PDF of this updated PRD

### 12.2 Live Demonstration Requirements (Stage 2)
- [ ] Physical ESP32 node connected to laptop via USB or local WiFi
- [ ] Relay board with LED indicators showing actuation
- [ ] Oscilloscope or logic analyzer showing <25 ms trigger latency
- [ ] Demonstration of fail-safe behavior (WiFi disconnect → watchdog reset → relays release)