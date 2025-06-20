from flask import Flask, render_template, request
import paho.mqtt.publish as publish
import uuid
import os
import threading  # <-- Nuevas importaciones
import requests   # <-- Nuevas importaciones
import time       # <-- Nuevas importaciones

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

# ==========================================================
# CÓDIGO PARA MANTENER LA APP ACTIVA (SOLO PLAN FREE)
# ==========================================================
def keep_alive():
    """Envía un ping periódico para evitar que la app se duerma"""
    while True:
        try:
            # ¡IMPORTANTE! Cambia por TU URL de Render
            requests.get("https://proyecto-esp32-flask-2.onrender.com")
            print("✅ Ping enviado para mantener activa la app")
        except Exception as e:
            print(f"⚠️ Error en ping: {str(e)}")
        time.sleep(600)  # Ping cada 10 minutos (600 segundos)

# ==========================================================
# INICIO DE LA APLICACIÓN
# ==========================================================
if __name__ == "__main__":
    # Inicia el hilo que mantendrá la app despierta
    t = threading.Thread(target=keep_alive)
    t.daemon = True  # El hilo se cerrará cuando la app principal termine
    t.start()
    
    # Inicia el servidor Flask
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
