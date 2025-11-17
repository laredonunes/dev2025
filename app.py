from flask import (
    Flask, send_from_directory, request, jsonify, render_template,
    redirect, url_for, session, g, flash
)
from functools import wraps
import os
import time
from collections import deque
import socket
import sqlite3
import psutil
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# --- Inicialização e Configuração ---
load_dotenv() # Carrega variáveis do .env

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECURITY_ENABLED'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'app.db')

#-----------------------------------------------------------------------
# BLOCO DO BANCO DE DADOS
#-----------------------------------------------------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            password_reset_required BOOLEAN DEFAULT TRUE
        )
    """)
    db.commit()

def get_user_by_username(username: str):
    return get_db().execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()

def get_all_users():
    return get_db().execute("SELECT id, username FROM user").fetchall()

def create_admin_user_if_not_exists():
    admin_user = os.getenv('DEFAULT_ADMIN_USER', 'admin')
    if get_user_by_username(admin_user) is None:
        admin_pass = os.getenv('DEFAULT_ADMIN_PASSWORD', 'changeme')
        hashed_password = generate_password_hash(admin_pass)
        get_db().execute(
            "INSERT INTO user (username, password, password_reset_required) VALUES (?, ?, ?)",
            (admin_user, hashed_password, True)
        )
        get_db().commit()

#-----------------------------------------------------------------------
# BLOCO DE SEGURANÇA E DECORATORS
#-----------------------------------------------------------------------
failed_attempts = {}
blocked_ips = {}
request_log = deque(maxlen=100)
BLOCK_DURATIONS = [3600]

def get_remote_address():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()

@app.after_request
def log_request(response):
    # ... (código do log_request mantido)
    return response

def security_check(f):
    # ... (código do security_check mantido)
    return f

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        if session.get('password_reset_required', False):
            return redirect(url_for('change_password_page'))
        return f(*args, **kwargs)
    return decorated_function

#-----------------------------------------------------------------------
# ROTAS DE AUTENTICAÇÃO E GERENCIAMENTO DE USUÁRIOS
#-----------------------------------------------------------------------
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html', error_modal=None)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password_page():
    if 'logged_in' not in session:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or new_password != confirm_password:
            flash('As senhas não conferem ou estão vazias.', 'error')
            return render_template('change_password.html')

        hashed_password = generate_password_hash(new_password)
        db = get_db()
        db.execute("UPDATE user SET password = ?, password_reset_required = FALSE WHERE id = ?", (hashed_password, session['user_id']))
        db.commit()

        session['password_reset_required'] = False
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('change_password.html')

@app.route('/manage-users')
@login_required
def manage_users_page():
    users = get_all_users()
    return render_template('manage_users.html', users=users)

#-----------------------------------------------------------------------
# ROTAS DA API
#-----------------------------------------------------------------------
@app.route('/api/login', methods=['POST'])
@security_check
def api_login():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return jsonify({"error": "Nome de usuário e senha são obrigatórios."}), 400

    user = get_user_by_username(username)
    if user and check_password_hash(user['password'], password):
        session['logged_in'] = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['password_reset_required'] = user['password_reset_required']
        
        if get_remote_address() in failed_attempts:
            del failed_attempts[get_remote_address()]

        if user['password_reset_required']:
            return jsonify({"success": True, "redirect_url": url_for('change_password_page')})
        else:
            return jsonify({"success": True, "redirect_url": url_for('dashboard')})
    else:
        # ... (código do record_failed_attempt mantido)
        return jsonify({"success": False, "error": "Credenciais inválidas."}), 401

@app.route('/api/users', methods=['POST'])
@login_required
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios."}), 400
    
    if get_user_by_username(username):
        return jsonify({"error": "Este nome de usuário já existe."}), 409

    hashed_password = generate_password_hash(password)
    db = get_db()
    db.execute("INSERT INTO user (username, password, password_reset_required) VALUES (?, ?, ?)", (username, hashed_password, False))
    db.commit()
    
    return jsonify({"success": True, "message": f"Usuário '{username}' criado com sucesso."}), 201

# ... (outras rotas da API e do app mantidas)
#-----------------------------------------------------------------------
# ROTAS DO PAINEL
#-----------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    # ... (código do dashboard mantido)
    pass

@app.route('/monitoring')
@login_required
def monitoring():
    # ... (código do monitoring mantido)
    pass

# ... (resto do arquivo)
if __name__ == '__main__':
    with app.app_context():
        init_db()
        create_admin_user_if_not_exists()
    app.run(host='0.0.0.0', port=5000, debug=True)
