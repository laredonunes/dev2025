from flask import (
    Flask, send_from_directory, request, jsonify, render_template,
    redirect, url_for, session, g, flash, abort
)
from functools import wraps
import os
import time
import secrets
import string
from collections import deque, Counter
import socket
import sqlite3
import psutil
import redis
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Importa o Blueprint dos agentes
from agents import agents
from celery_utils import make_celery
from celery.signals import worker_ready
from biblioteca_fila import get_queue_info

# Import local para evitar dependência circular no topo
from database import (
    init_db, migrate_db, get_user_by_username, get_all_users, delete_user_by_id, get_db, init_app as init_db_app
)

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECURITY_ENABLED'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'app.db')


#-----------------------------------------------------------------------
# BLOCO DE CONFIGURAÇÃO DO CELERY
#-----------------------------------------------------------------------
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '16379')

app.config.update(
    CELERY_BROKER_URL=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    CELERY_RESULT_BACKEND=f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
)
celery = make_celery(app)
celery.set_default()

# ... (restante do seu código)

#-----------------------------------------------------------------------
# Gerenciamento de site
#-----------------------------------------------------------------------
@app.route('/')
def index():
    index_base = os.getenv('PAGINA_INDEX', 'login')
    if index_base == "login":
        return redirect(url_for('login_page'))
    elif index_base == "text":
        return jsonify({"message": "API está funcional"})
    elif index_base == "index":
        return redirect(url_for('servir_pagina_estatica', nome_pagina=index_base))
    else:
        return redirect(url_for('login_page'))

@app.route('/site/<path:nome_pagina>')
def servir_pagina_estatica(nome_pagina):
    return send_from_directory('site/html', f"{nome_pagina}.html")

# --- NOVA ROTA PARA IMAGENS ---
@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve uma imagem diretamente da pasta site/images."""
    return send_from_directory(os.path.join('site', 'images'), filename)

#-----------------------------------------------------------------------
# COMANDOS CLI PARA GERENCIAMENTO
#-----------------------------------------------------------------------
# ... (restante do seu código)

if __name__ == '__main__':
    with app.app_context():
        init_app_command()
    app.run(host='0.0.0.0', port=5000, debug=True)
