import os
import time
import json
import random
import librosa
import numpy as np
import paho.mqtt.client as mqtt

# Configuration parameters
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = "audio/alerts"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

print("--- Starting SafeSite Acoustic Anomaly Detector ---")

# Connect to Local MQTT Broker
client = mqtt.Client("AcousticAnalyzer")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    print(f"📡 Connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"❌ Failed to connect to MQTT Broker: {e}")

def analyze_audio_signature(audio_path):
    """
    Extracts audio features (MFCCs) to simulate how a 1D CNN/YAMNet 
    processes edge audio signals.
    """
    try:
        # Load audio (downsampled to 16kHz for edge efficiency)
        y, sr = librosa.load(audio_path, sr=16000, duration=2.0)
        
        # Extract features (MFCCs)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mean_mfccs = np.mean(mfccs.T, axis=0)
        
        print(f"📊 Processed signature matrix for {os.path.basename(audio_path)}")
        return mean_mfccs
    except Exception as e:
        print(f"⚠️ Error parsing audio file: {e}")
        return None

def trigger_acoustic_alert(anomaly_type, confidence):
    """Publishes a structured safety event to the MQTT broker."""
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "module": "audio_analyzer",
        "event": "acoustic_anomaly",
        "data": {
            "anomaly_type": anomaly_type,
            "confidence": round(confidence, 2)
        }
    }
    
    client.publish(MQTT_TOPIC, json.dumps(payload))
    print(f"🚨 [ALERT SENT] {anomaly_type.upper()} detected with {confidence*100}% confidence.")

# Core processing loop
try:
    if DEMO_MODE:
        print("🪵 Running in Demo Mode: Simulating factory floor acoustics...")
        anomalies = ["metal_screech", "operator_scream", "heavy_impact"]
        
        while True:
            # Simulate an idle machine environment for a random period
            time.sleep(random.randint(8, 15))
            
            # Select a random anomaly to simulate injection
            detected = random.choice(anomalies)
            conf = random.uniform(0.85, 0.98)
            
            print(f"\n🔊 [Acoustic Event Caught] Processing rolling 2-second audio window...")
            # Simulate feature processing delay
            time.sleep(0.5) 
            
            trigger_acoustic_alert(detected, conf)
    else:
        print("🎤 Running in Live Mode: Awaiting edge stream buffers...")
        # Implementation for real-time soundcard audio chunk loops goes here
        while True:
            time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Shutting down acoustic services safely.")
    client.loop_stop()
    client.disconnect()