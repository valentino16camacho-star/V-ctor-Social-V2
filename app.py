import eventlet
eventlet.monkey_patch()

import os, time, json, random, uuid
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename # Importante para limpiar nombres de archivos

app = Flask(__name__)
app.secret_key = 'sullana_ultra_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- CONFIGURACIÓN DE SUBIDAS ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Creamos la carpeta automáticamente si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --------------------------------

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
    
    user_info = db['usuarios'].get(session['usuario'], {})
    
    return render_template('index.html', 
                           posts=db['posts'], 
                           usuario=session['usuario'],
                           bio=user_info.get('bio', 'Sin biografía.'),
                           avatar=user_info.get('avatar', 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png'))

# --- RUTA PARA RECIBIR ARCHIVOS DE LA PC ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'usuario' not in session:
        return "No autorizado", 401
    
    if 'file' not in request.files:
        return "No hay archivo", 400
        
    file = request.files['file']
    if file.filename == '':
        return "Nombre vacío", 400
        
    if file and allowed_file(file.filename):
        # Creamos nombre único con tiempo para evitar duplicados
        filename = secure_filename(file.filename)
        nuevo_nombre = f"{int(time.time())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], nuevo_nombre))
        
        # Devolvemos la ruta relativa para que el navegador la encuentre
        return f"/static/uploads/{nuevo_nombre}"
    
    return "Tipo de archivo no permitido", 400

@app.route('/perfil/<nombre_usuario>')
def ver_perfil(nombre_usuario):
    if 'usuario' not in session: 
        return redirect(url_for('login'))
    
    db = cargar_datos()
    if nombre_usuario not in db['usuarios']: 
        return "Usuario no encontrado", 404
    
    user_info = db['usuarios'][nombre_usuario]
    user_posts = [p for p in db['posts'] if p.get('usuario') == nombre_usuario]
    
    return render_template('perfil.html', 
                           perfil_nombre=nombre_usuario, 
                           bio=user_info.get('bio', ''), 
                           avatar=user_info.get('avatar', 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png'),
                           posts=user_posts,
                           usuario_actual=session['usuario'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form.get('nombre').upper().strip()
        codigo = request.form.get('codigo').strip()
        db = cargar_datos()
        
        user_data = db['usuarios'].get(nombre)
        
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
        
        db['usuarios'][nombre] = {
            "codigo": nuevo_codigo,
            "bio": "¡Hola! Soy nuevo en Sullana Social.",
            "avatar": "https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png"
        }
        guardar_datos(db)
        
        return f"<h1>¡Registrado!</h1><p>Tu código es: <b>{nuevo_codigo}</b>. Guárdalo bien.</p><a href='/login'>Ir al Login</a>"
    return render_template('registro.html')

@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'usuario' in session:
        db = cargar_datos()
        nombre = session['usuario']
        
        nueva_bio = request.form.get('bio')
        nueva_foto = request.form.get('foto_url')
        
        if nombre in db['usuarios']:
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
        user_info = db['usuarios'].get(session['usuario'], {})
        # Verificación de seguridad para el avatar
        if isinstance(user_info, dict):
            foto = user_info.get('avatar', 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png')
        else:
            foto = 'https://www.redditstatic.com/avatars/defaults/v2/avatar_default_1.png'

        nuevo_post = {
            "id": str(uuid.uuid4()),
            "usuario": session['usuario'],
            "avatar": foto,
            "contenido": data['contenido'],
            "media_url": data.get('media_url', ''),
            "hora": time.strftime("%H:%M")
        }
        
        db['posts'].insert(0, nuevo_post)
        guardar_datos(db)
        emit('publicacion_instantanea', nuevo_post, broadcast=True)

@socketio.on('borrar_post')
def eliminar_post(post_id):
    if 'usuario' in session:
        db = cargar_datos()
        post_a_borrar = next((p for p in db['posts'] if p.get('id') == post_id), None)
        
        if post_a_borrar and post_a_borrar['usuario'] == session['usuario']:
            db['posts'] = [p for p in db['posts'] if p.get('id') != post_id]
            guardar_datos(db)
            emit('post_eliminado', post_id, broadcast=True)

if __name__ == '__main__':
    socketio.run(app)
