from flask import Flask, render_template, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import threading
import time
import uuid
import os
import json
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, async_mode='eventlet', ping_timeout=300, ping_interval=60)

# Configuración MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_LED = f"usuario_{uuid.uuid4().hex[:4]}/led"
MQTT_TOPIC_DHT = f"usuario_{uuid.uuid4().hex[:4]}/dht"

print(f"✅ Tópico MQTT para LED: {MQTT_TOPIC_LED}")
print(f"✅ Tópico MQTT para DHT22: {MQTT_TOPIC_DHT}")

# Variables para almacenar los datos del sensor
humidity_value = 50.0
temperature_value = 25.0
last_values = {'humidity': 0.0, 'temperature': 0.0}

# Configuración del cliente MQTT
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

def on_connect(client, userdata, flags, rc):
    print("✅ Conectado al broker MQTT")
    client.subscribe(MQTT_TOPIC_DHT)

def on_message(client, userdata, msg):
    global humidity_value, temperature_value, last_values
    try:
        data = json.loads(msg.payload.decode())
        new_humidity = round(float(data['humidity']), 1)
        new_temperature = round(float(data['temperature']), 1)
        
        # Solo actualizar si hay cambio significativo
        if (abs(new_humidity - last_values['humidity']) > 0.1 or 
            abs(new_temperature - last_values['temperature']) > 0.1):
            
            humidity_value = new_humidity
            temperature_value = new_temperature
            last_values = {'humidity': humidity_value, 'temperature': temperature_value}
            
            print(f"📊 Sensor: {humidity_value}% humedad, {temperature_value}°C")
            socketio.emit('dht_update', {
                'humidity': humidity_value,
                'temperature': temperature_value
            })
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"❌ Error en datos MQTT: {str(e)}")

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
        return f"💡 Comando {command} enviado"
    return render_template(
        "control_led.html",
        topic_led=MQTT_TOPIC_LED,
        topic_dht=MQTT_TOPIC_DHT,
        initial_humidity=humidity_value,
        initial_temperature=temperature_value
    )

@app.route("/health")
def health_check():
    return "OK", 200

def keep_alive():
    while True:
        try:
            # IMPORTANTE: Reemplazar con tu URL de Render
            requests.get("https://proyecto-esp32-flask.onrender.com/health", timeout=10)
            print("❤️  Ping de keep-alive enviado")
        except Exception as e:
            print(f"⚠️ Error en keep-alive: {str(e)}")
        time.sleep(300)  # Ping cada 5 minutos

if __name__ == "__main__":
    # Iniciar el hilo para mantener la app despierta
    threading.Thread(target=keep_alive, daemon=True).start()
    
    # Iniciar el servidor Flask con SocketIO
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host='0.0.0.0', port=port)