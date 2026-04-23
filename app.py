import eventlet
eventlet.monkey_patch() # Esto es el secreto para que Render no falle

import os, time, json
from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'sullana_omega_2026'
# Esto configura el tiempo real de forma profesional
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DB_PATH = 'datos.json'

def cargar_datos():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r') as f: return json.load(f)
    return {"posts": []}

def guardar_datos(data):
    with open(DB_PATH, 'w') as f: json.dump(data, f, indent=4)

@app.route('/')
def index():
    data = cargar_datos()
    return render_template('index.html', posts=data['posts'])

# Cuando alguien publica, SocketIO se encarga de avisar a TODOS
@socketio.on('enviar_post')
def manejar_post(data):
    nuevo_post = {
        "usuario": data['usuario'],
        "contenido": data['contenido'],
        "hora": time.strftime("%H:%M")
    }
    
    # Guardamos en el JSON
    db = cargar_datos()
    db['posts'].insert(0, nuevo_post)
    guardar_datos(db)
    
    # ¡MAGIA! Reenviamos el post a todos los que tengan la página abierta
    emit('publicacion_instantanea', nuevo_post, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)