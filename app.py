from flask import Flask, render_template, request
import paho.mqtt.publish as publish
import uuid

app = Flask(__name__)

# Configuración MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = f"usuario_{uuid.uuid4().hex[:4]}/led"

print(f"✅ Tópico MQTT único generado: {MQTT_TOPIC}")

@app.route("/", methods=["GET", "POST"])
def control_led():
    if request.method == "POST":
        command = request.form.get("command")
        publish.single(MQTT_TOPIC, command, hostname=MQTT_BROKER)
        return f"Comando enviado: {command} al tópico: {MQTT_TOPIC}"
    return render_template("control_led.html", topic=MQTT_TOPIC)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)