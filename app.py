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
    return {"posts": [], "usuarios": {}}

def guardar_datos(data):
    with open(DB_PATH, 'w') as f: json.dump(data, f, indent=4)

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    db = cargar_datos()
    
    # Obtenemos info del usuario actual
    user_info = db['usuarios'].get(session['usuario'], {})
    
    # Pasamos todo al HTML
    return render_template('index.html', 
                           posts=db['posts'], 
                           usuario=session['usuario'],
                           bio=user_info.get('bio', 'Sin biografía.'),
                           avatar=user_info.get('avatar', 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form.get('nombre').upper().strip()
        codigo = request.form.get('codigo').strip()
        db = cargar_datos()
        
        user_data = db['usuarios'].get(nombre)
        
        # Verificamos si es el formato nuevo (dict) o el viejo (str)
        if user_data:
            pin_registrado = user_data['codigo'] if isinstance(user_data, dict) else user_data
            if pin_registrado == codigo:
                session['usuario'] = nombre
                return redirect(url_for('index'))
                
        return "Código incorrecto o usuario no registrado", 401
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre').upper().strip()
        db = cargar_datos()
        
        if nombre in db['usuarios']:
            return "Ese nombre ya existe", 400
        
        nuevo_codigo = str(random.randint(1000, 9999))
        
        # Guardamos como objeto para incluir bio y foto después
        db['usuarios'][nombre] = {
            "codigo": nuevo_codigo,
            "bio": "¡Hola! Soy nuevo en Sullana Social.",
            "avatar": "https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png"
        }
        guardar_datos(db)
        
        return f"<h1>¡Registrado!</h1><p>Tu código es: <b>{nuevo_codigo}</b>. Guárdalo bien.</p><a href='/login'>Ir al Login</a>"
    return render_template('registro.html')

# NUEVA RUTA: Para actualizar la Bio y la Foto
@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'usuario' in session:
        db = cargar_datos()
        nombre = session['usuario']
        
        nueva_bio = request.form.get('bio')
        nueva_foto = request.form.get('foto_url')
        
        if nombre in db['usuarios']:
            # Si el usuario era del formato viejo, lo convertimos
            if not isinstance(db['usuarios'][nombre], dict):
                old_pin = db['usuarios'][nombre]
                db['usuarios'][nombre] = {"codigo": old_pin}
            
            db['usuarios'][nombre]['bio'] = nueva_bio
            db['usuarios'][nombre]['avatar'] = nueva_foto
            guardar_datos(db)
            
    return redirect(url_for('index'))

@socketio.on('enviar_post')
def manejar_post(data):
    if 'usuario' in session:
        db = cargar_datos()
        # Buscamos la foto del usuario para que el post la tenga
        user_info = db['usuarios'].get(session['usuario'], {})
        foto = user_info.get('avatar', 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png') if isinstance(user_info, dict) else 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png'

        nuevo_post = {
            "usuario": session['usuario'],
            "avatar": foto, # Añadimos la foto al post
            "contenido": data['contenido'],
            "hora": time.strftime("%H:%M")
        }
        
        db['posts'].insert(0, nuevo_post)
        guardar_datos(db)
        emit('publicacion_instantanea', nuevo_post, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)
