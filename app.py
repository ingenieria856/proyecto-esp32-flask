from flask import Flask, render_template, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import threading
import time
import uuid
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app)

# Configuración MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_LED = f"usuario_{uuid.uuid4().hex[:4]}/led"
MQTT_TOPIC_DHT = f"usuario_{uuid.uuid4().hex[:4]}/dht"  # Tópico para datos del DHT22

print(f"✅ Tópico MQTT para LED: {MQTT_TOPIC_LED}")
print(f"✅ Tópico MQTT para DHT22: {MQTT_TOPIC_DHT}")

# Variables para almacenar los datos del sensor
humidity_value = 50
temperature_value = 25

# Configuración del cliente MQTT
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

def on_connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT")
    client.subscribe(MQTT_TOPIC_DHT)

def on_message(client, userdata, msg):
    global humidity_value, temperature_value
    if msg.topic == MQTT_TOPIC_DHT:
        try:
            # El payload es un JSON con humedad y temperatura
            data = json.loads(msg.payload.decode())
            humidity_value = data['humidity']
            temperature_value = data['temperature']
            print(f"Recibido: humedad={humidity_value}%, temperatura={temperature_value}°C")
            # Enviar a todos los clientes WebSocket
            socketio.emit('dht_update', {
                'humidity': humidity_value,
                'temperature': temperature_value
            })
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            print(f"Error al procesar datos: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Iniciar el loop MQTT en un hilo separado
mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
mqtt_thread.daemon = True
mqtt_thread.start()

@app.route("/", methods=["GET", "POST"])
def control_led():
    if request.method == "POST":
        command = request.form.get("command")
        mqtt_client.publish(MQTT_TOPIC_LED, command)
        return f"Comando enviado: {command} al tópico: {MQTT_TOPIC_LED}"
    return render_template(
        "control_led.html",
        topic_led=MQTT_TOPIC_LED,
        topic_dht=MQTT_TOPIC_DHT,
        initial_humidity=humidity_value,
        initial_temperature=temperature_value
    )

# Función para mantener la app activa (solo para plan free de Render)
def keep_alive():
    import requests
    while True:
        try:
            # ¡IMPORTANTE! Cambia por TU URL de Render
            requests.get("https://proyecto-esp32-flask-2.onrender.com")
            print("✅ Ping enviado para mantener activa la app")
        except Exception as e:
            print(f"⚠️ Error en ping: {str(e)}")
        time.sleep(600)

if __name__ == "__main__":
    # Iniciar el hilo para mantener la app despierta
    t = threading.Thread(target=keep_alive)
    t.daemon = True
    t.start()
    
    # Iniciar el servidor Flask con SocketIO
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)