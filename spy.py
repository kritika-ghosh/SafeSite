import paho.mqtt.client as mqtt
print("in")
def on_message(client, userdata, msg):
    print(f"📡 Spy Caught Data on channel [{msg.topic}]:\n{msg.payload.decode()}\n")

client = mqtt.Client("TerminalSpy")
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("audio/alerts")
client.loop_forever()