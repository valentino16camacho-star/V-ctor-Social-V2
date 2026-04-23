import eventlet
eventlet.monkey_patch()

import os, time, json, random
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'sullana_ultra_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DB_PATH = 'datos.json'

def cargar_datos():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'r') as f: return json.load(f)
    return {"posts": [], "usuarios": {}} # Agregamos sección de usuarios

def guardar_datos(data):
    with open(DB_PATH, 'w') as f: json.dump(data, f, indent=4)

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    data = cargar_datos()
    return render_template('index.html', posts=data['posts'], usuario=session['usuario'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form.get('nombre').upper()
        codigo = request.form.get('codigo')
        db = cargar_datos()
        
        # Verificar si el usuario existe y el código coincide
        if nombre in db['usuarios'] and db['usuarios'][nombre] == codigo:
            session['usuario'] = nombre
            return redirect(url_for('index'))
        return "Código incorrecto o usuario no registrado", 401
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre').upper()
        db = cargar_datos()
        
        if nombre in db['usuarios']:
            return "Ese nombre ya existe", 400
        
        # Generar código aleatorio de 4 dígitos
        nuevo_codigo = str(random.randint(1000, 9999))
        db['usuarios'][nombre] = nuevo_codigo
        guardar_datos(db)
        
        return f"<h1>¡Registrado!</h1><p>Tu código es: <b>{nuevo_codigo}</b>. Guárdalo bien para iniciar sesión.</p><a href='/login'>Ir al Login</a>"
    return render_template('registro.html')

@socketio.on('enviar_post')
def manejar_post(data):
    if 'usuario' in session:
        nuevo_post = {
            "usuario": session['usuario'],
            "contenido": data['contenido'],
            "hora": time.strftime("%H:%M")
        }
        db = cargar_datos()
        db['posts'].insert(0, nuevo_post)
        guardar_datos(db)
        emit('publicacion_instantanea', nuevo_post, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)
