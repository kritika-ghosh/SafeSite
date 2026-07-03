# SafeSite-Edge Pro – System Architecture

> **Tata Technologies InnoVent Hackathon** · Track: Edge AI for Operator Safety & Human–Machine Interaction

---

```mermaid
graph TD
    %% ── LIGHT THEME STYLES ──────────────────────────────────
    classDef sensor   fill:#eff6ff,stroke:#4f46e5,stroke-width:2px,color:#1e1b4b
    classDef orch     fill:#f0f9ff,stroke:#0369a1,stroke-width:2px,color:#0c4a6e
    classDef cv       fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px,color:#2e1065
    classDef audio    fill:#faf5ff,stroke:#7e22ce,stroke-width:2px,color:#3b0764
    classDef rag      fill:#ecfeff,stroke:#0891b2,stroke-width:2px,color:#083344
    classDef broker   fill:#fdf4ff,stroke:#9333ea,stroke-width:2px,color:#4a044e
    classDef bridge   fill:#f0fdfa,stroke:#0d9488,stroke-width:2px,color:#042f2e
    classDef hw       fill:#fff7ed,stroke:#c2410c,stroke-width:2px,color:#431407
    classDef relay    fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#451a03
    classDef ui       fill:#f0fdf4,stroke:#15803d,stroke-width:2px,color:#052e16
    classDef danger   fill:#fef2f2,stroke:#dc2626,stroke-width:2px,color:#450a0a

    %% ── ROW 1 · SENSORS ────────────────────────────────────
    subgraph SEN ["📡  SENSORS  —  On-Machine Hardware"]
        direction LR
        CAM_I["🎥 IR Camera\nCabin-Facing"]:::sensor
        CAM_E["🎥 Wide-Angle Camera\nPerimeter / Blind-Spot"]:::sensor
        MIC["🎙️ Microphone\nAudio Capture"]:::sensor
    end

    %% ── ROW 2 · ORCHESTRATOR ───────────────────────────────
    ORCH["⚙️  FastAPI Orchestrator\nLoads all quantized models at boot\nManages MQTT event bus · Serves RAG /query endpoint"]:::orch

    %% ── ROW 3 · AI STACK  (TB keeps MQTT centred below) ────
    subgraph AI ["🧠  6-LAYER AI STACK  —  Single Edge Node  ·  100% Air-Gapped  ·  less than 5.5 GB VRAM total"]
        direction TB

        M1["M1 · Cabin Guardian\n──────────────────────────────────\n📥 IR camera  ·  MediaPipe Face Mesh (0.10)\nEAR + MAR over 30-frame window  →  2-layer GRU (FP32)\n📤 cabin/fatigue  ·  less than 10 ms/frame  ·  400 MB RAM"]:::cv

        M23["M2+M3 · Unified Perimeter & PPE Sentinel\n──────────────────────────────────\n📥 Wide-angle camera  ·  YOLOv10-Nano INT8 (ONNX Runtime)  ·  Single pass\n4 classes: person_with_ppe  ·  person_no_ppe  ·  machinery  ·  hazard\n+ Monocular distance estimation (known camera height + focal length)\n📤 perimeter/alert  ·  30 FPS  ·  1.2 GB VRAM"]:::cv

        M4["M4 · Acoustic Anomaly Detector\n──────────────────────────────────\n📥 Microphone  ·  YAMNet TFLite INT8  ·  Separate CPU thread\n2-sec windows · 1-sec overlap  ·  Subset of ESC-50\nClasses: scream  ·  glass_break  ·  metal_grind  ·  explosion  ·  shout\n📤 audio/anomaly  ·  200 MB RAM  ·  No GPU required"]:::audio

        M5["M5 · Gesture Emergency Stop\n──────────────────────────────────\n📥 Wide-angle camera (every 5th frame, CPU-saving)\nMediaPipe Hands  →  21 keypoints/hand  →  LSTM (2 layers · 64 units)\nGestures: STOP  ·  HELP  ·  EMERGENCY_STOP\n⚡ Conditional: activated by M23 only when person in 5m zone\n📤 gesture/trigger  ·  150 MB RAM (conditional)"]:::cv

        M6["M6 · Offline RAG Safety Assistant\n──────────────────────────────────\n📥 HTTP POST /query  ·  Phi-3-mini-4k-instruct INT4 (Ollama / llama.cpp)\n20 layers GPU-offloaded  ·  3.2 GB VRAM+RAM\nChromaDB + all-MiniLM-L6-v2 (FP16)  ·  90 MB embeddings\nSources: Tata Safety Handbook  ·  OSHA  ·  JCB Maintenance Manual\n📤 answer + page citation  ·  RAG less than 150 ms  ·  LLM more than 15 tok/s"]:::rag
    end

    %% ── ROW 4 · MQTT BROKER (centred below TB stack) ────────
    MQTT["📨  Local MQTT Broker  —  Eclipse Mosquitto 2.0  ·  localhost:1883\nZero cloud dependency  ·  All communication on local LAN"]:::broker

    %% ── ROW 5 · OUTPUT SPLIT ────────────────────────────────
    subgraph OUT ["OUTPUT LAYER"]
        direction LR
        WS["🔁 WebSocket Bridge\nMQTT → JSON  ·  ws://localhost:8765\n10+ events / sec\nStandard browser API — no plugins"]:::bridge
        ESP["🔌 ESP32 Actuator Node\nPubSubClient MQTT  ·  localhost:1883\nSubscribes: actuation/emergency_stop\n  actuation/warning_strobe\n  actuation/reset\nPublishes: esp32/heartbeat every 2 s\nWatchdog: resets after 30 s silence"]:::hw
    end

    %% ── ROW 6 · CONSUMERS ──────────────────────────────────
    subgraph CON ["CONSUMERS"]
        direction LR
        DASH["🟢  React Operator Dashboard\n📊 Real-time Alert Feed\n🤖 RAG Safety Chatbot\n📋 Event Log & History"]:::ui
        RLY["⚡  4-Ch Optocoupler Relay Board\nGPIO 16 → R1 Throttle Kill  (NC Failsafe)\nGPIO 17 → R2 24V Strobe Light\nGPIO 18 → R3 24V Siren Module\nGPIO 19 → R4 Spare Brake Actuation\n5V DC control · 10A contacts"]:::relay
    end

    %% ── ROW 7 · MACHINE INTERVENTION ───────────────────────
    MCH["🚧  MACHINE INTERVENTION\nThrottle Signal Grounded  ·  Strobe + Siren Activated\nNC relay opens on trigger — fails safe  ·  less than 25 ms end-to-end"]:::danger

    %% ── SENSOR → ORCHESTRATOR → AI ─────────────────────────
    SEN  -->|"raw sensor inputs"| ORCH
    ORCH -->|"boots & manages all modules"| AI

    %% ── DIRECT SENSOR FEEDS ─────────────────────────────────
    CAM_I -->|"30 FPS"| M1
    CAM_E -->|"30 FPS"| M23
    CAM_E -.->|"every 5th frame\nonly when gate open"| M5
    MIC   -->|"audio stream"| M4

    %% ── CONDITIONAL ACTIVATION GATE ────────────────────────
    M23 -->|"🔑 person in 5m zone?\nelse M5 SLEEPS"| M5

    %% ── MODULES → MQTT ──────────────────────────────────────
    M1  -->|"cabin/fatigue"| MQTT
    M23 -->|"perimeter/alert"| MQTT
    M4  -->|"audio/anomaly"| MQTT
    M5  -->|"gesture/trigger"| MQTT

    %% ── MQTT → OUTPUT SPLIT ─────────────────────────────────
    MQTT -->|"all detection events"| WS
    MQTT -->|"actuation commands\nvia LAN Wi-Fi"| ESP

    %% ── OUTPUT → CONSUMERS ──────────────────────────────────
    WS  -->|"streaming JSON"| DASH
    ESP -->|"GPIO 16-19 high"| RLY

    %% ── RAG QUERY LOOP ─────────────────────────────────────
    DASH -->|"HTTP POST /query"| M6
    M6   -->|"answer + page citation"| DASH

    %% ── RELAY → MACHINE ────────────────────────────────────
    RLY -->|"NC failsafe break  ·  less than 25 ms"| MCH
```

---

## 📊 Performance Metrics at a Glance

| Module | Technology Stack | Quantization | Latency | Memory |
|--------|-----------------|-------------|---------|--------|
| **M1 · Cabin Guardian** | MediaPipe Face Mesh 0.10 + PyTorch GRU | FP32 (CPU) | <10 ms / frame | 400 MB RAM |
| **M2+M3 · Perimeter & PPE** | YOLOv10-Nano (ONNX Runtime) | INT8 | ≤25 ms/frame @ 30 FPS | **1.2 GB VRAM** |
| **M4 · Acoustic Anomaly** | YAMNet TFLite (MobileNet-v1) | INT8 | 2-sec sliding window | 200 MB RAM |
| **M5 · Gesture Stop** | MediaPipe Hands + TensorFlow LSTM | FP32 (CPU) | Conditional (sleeps when idle) | 150 MB RAM |
| **M6 · Embeddings** | Sentence-Transformers all-MiniLM-L6-v2 | FP16 | <150 ms retrieval | 90 MB RAM |
| **M6 · LLM Inference** | Phi-3-mini-4k-instruct-q4 (Ollama/llama.cpp) | INT4 (GGUF) | >15 tokens/sec | 3.2 GB VRAM+RAM |
| **ESP32 Actuation** | PubSubClient MQTT → NC Relay | – | **<25 ms end-to-end** | 4 MB Flash |
| **🔋 Total System** | All 6 modules concurrent | Mixed | – | **<5.5 GB VRAM** |

---

## 🔑 Architecture Optimisations (For Judges Q&A)

| Judge Concern | Engineering Solution |
|---------------|---------------------|
| "Running YOLO twice for PPE and perimeter is too slow." | A single **YOLOv10-Nano** is fine-tuned on 4 custom classes — PPE status and perimeter hazards detected in **one unified pass**. No weight swapping, no frame drops. |
| "MediaPipe Hands will constantly burn CPU." | M5 uses a **conditional activation gate** driven by M2+M3. If no person is inside the 5 m boundary zone, the gesture module never wakes — zero CPU overhead. |
| "React needs a MQTT browser plugin." | A **WebSocket proxy bridge** translates all MQTT events into clean JSON streamed over a single WS endpoint (`ws://localhost:8765`). Standard `WebSocket` API, no plugins. |
| "Can you really run an LLM + CV on one laptop?" | **Phi-3-mini INT4** uses 3.2 GB; **YOLO INT8** uses 1.2 GB. `llama.cpp` GPU-offloads 20 layers while YOLO runs concurrently. Total peak: <5.5 GB on RTX 3060. |
| "How do you guarantee physical actuation in remote mines?" | ESP32 connects to a **local Mosquitto broker** over LAN. Relay contacts interface directly with the machine throttle circuit. Zero internet, zero cloud. |
| "What if connectivity is completely lost?" | The system is **100% air-gapped**. All communication is local Ethernet/Wi-Fi between the edge node and ESP32 actuators — works underground. |
| "What if the ESP32 loses MQTT connection?" | A hardware **watchdog timer** resets the ESP32 if no MQTT keep-alive is received in 30 seconds, restoring the NC relay's fail-safe open state automatically. |

---

## 🔁 Data Flow Summary

```
Sensors ──► Orchestrator ──► AI Stack ──► MQTT Broker ──► WebSocket Bridge ──► React Dashboard
                                                    │                                   ↕ RAG
                                                    └──► ESP32 Actuator ──► 4-Ch Relay ──► Machine
```

> All communication is **local-only**. The edge node, MQTT broker, ESP32, and React dashboard share a single air-gapped LAN — operable in underground mines, remote construction sites, and any environment with zero connectivity.
