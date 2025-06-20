from flask import Flask, render_template, request
import paho.mqtt.publish as publish
import uuid  # Para generar un tópico único

app = Flask(__name__)

# Configuración MQTT (HiveMQ público)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883  # Usa 8883 para TLS

# Genera un tópico único automáticamente (ej: "usuario_7f3a/led")
MQTT_TOPIC = f"usuario_{uuid.uuid4().hex[:4]}/led"  # ¡Único para tu proyecto!

print(f"✅ Tópico MQTT único generado: {MQTT_TOPIC}")

@app.route("/", methods=["GET", "POST"])
def control_led():
    if request.method == "POST":
        command = request.form.get("command")
        # Publica el mensaje MQTT en el tópico único
        publish.single(
            MQTT_TOPIC,
            command,
            hostname=MQTT_BROKER,
            port=MQTT_PORT
        )
        return f"📩 Mensaje enviado: '{command}' al tópico: '{MQTT_TOPIC}'"
    return render_template("control_led.html", topic=MQTT_TOPIC)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)  # Render usa puerto dinámico