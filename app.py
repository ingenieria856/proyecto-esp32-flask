from flask import Flask, render_template, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import eventlet
import time
import uuid
import os
import json
import socket  # Importación añadida
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()

# IMPORTANTE: Usar async_mode='eventlet' y evitar threading
socketio = SocketIO(app, 
                   async_mode='eventlet', 
                   ping_timeout=300, 
                   ping_interval=60,
                   logger=True,
                   engineio_logger=True)

# Configuración MQTT - Usar IP directamente para evitar problemas DNS
MQTT_BROKER_IP = "3.121.206.95"  # IP de broker.hivemq.com (puede cambiar)
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

def connect_mqtt():
    """Función para conectar MQTT con reintentos"""
    max_retries = 5
    retry_delay = 3  # segundos
    
    for attempt in range(max_retries):
        try:
            logging.info(f"Intentando conexión MQTT (intento {attempt+1}/{max_retries})")
            mqtt_client.connect(MQTT_BROKER_IP, MQTT_PORT)
            logging.info("✅ Conectado al broker MQTT")
            return True
        except (socket.gaierror, ConnectionRefusedError, OSError) as e:
            logging.error(f"Error de conexión MQTT: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logging.error("⚠️ No se pudo conectar al broker MQTT después de varios intentos")
    return False

def on_connect(client, userdata, flags, rc):
    logging.info("✅ Conectado al broker MQTT")
    client.subscribe(MQTT_TOPIC_DHT)

def on_message(client, userdata, msg):
    global humidity_value, temperature_value, last_values
    try:
        data = json.loads(msg.payload.decode())
        new_humidity = round(float(data.get('humidity', 0)), 1)
        new_temperature = round(float(data.get('temperature', 0)), 1)
        
        # Solo actualizar si hay cambio significativo
        if (abs(new_humidity - last_values['humidity']) > 0.1 or 
            abs(new_temperature - last_values['temperature']) > 0.1):
            
            humidity_value = new_humidity
            temperature_value = new_temperature
            last_values = {'humidity': humidity_value, 'temperature': temperature_value}
            
            logging.info(f"📊 Sensor: {humidity_value}% humedad, {temperature_value}°C")
            socketio.emit('dht_update', {
                'humidity': humidity_value,
                'temperature': temperature_value
            })
    except (ValueError, KeyError, json.JSONDecodeError, TypeError) as e:
        logging.error(f"❌ Error en datos MQTT: {str(e)}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

@app.route("/", methods=["GET", "POST"])
def control_led():
    if request.method == "POST":
        command = request.form.get("command")
        try:
            mqtt_client.publish(MQTT_TOPIC_LED, command)
            logging.info(f"💡 Comando {command} enviado")
            return f"💡 Comando {command} enviado"
        except Exception as e:
            logging.error(f"Error publicando MQTT: {str(e)}")
            return "Error al enviar comando", 500
            
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

def start_mqtt():
    """Inicia el loop MQTT usando eventlet"""
    if connect_mqtt():
        mqtt_client.loop_start()
    else:
        logging.error("No se pudo iniciar MQTT")

if __name__ == "__main__":
    # Iniciar MQTT usando eventlet
    eventlet.spawn(start_mqtt)
    
    # Iniciar el servidor Flask con SocketIO
    port = int(os.environ.get("PORT", 8000))
    
    # IMPORTANTE: Usar 0 workers para evitar problemas con WebSockets
    socketio.run(app, 
                 host='0.0.0.0', 
                 port=port,
                 debug=False,
                 use_reloader=False,
                 log_output=True)