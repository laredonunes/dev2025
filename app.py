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
# Lê a porta do Redis da variável de ambiente, com '16379' como padrão.
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '16379')

app.config.update(
    CELERY_BROKER_URL=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    CELERY_RESULT_BACKEND=f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
)
celery = make_celery(app)
# Garante que este app Celery seja o "default" usado por @shared_task
celery.set_default()

# --- LOG DE VERIFICAÇÃO DE CONFIGURAÇÃO ---
print("\n" + "="*60)
print("🔍 VERIFICANDO CONFIGURAÇÕES DE CONEXÃO (app.py)")
print(f"  - REDIS_HOST lido do .env: '{REDIS_HOST}'")
print(f"  - REDIS_PORT lido do .env: '{REDIS_PORT}'")
print(f"  - URL do Broker Celery: '{app.config['CELERY_BROKER_URL']}'")
print(f"  - URL do Backend de Resultados Celery: '{app.config['CELERY_RESULT_BACKEND']}'")
print("="*60 + "\n")

# Inicializa o módulo de banco de dados com a aplicação
init_db_app(app)

# Anexa a conexão com o Redis ao app para ser usada em toda a aplicação
app.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Constantes de Segurança
FAILED_ATTEMPT_WINDOW = 300  # 5 minutos em segundos
MAX_FAILED_ATTEMPTS = 5
# Lê o cooldown da API do agente do .env, com 15s como padrão.
app.config['AGENT_API_COOLDOWN_SECONDS'] = int(os.getenv('AGENT_API_COOLDOWN_SECONDS', '15'))

@worker_ready.connect
def check_connections_on_worker_start(sender, **kwargs):
    """
    Executado quando um worker do Celery está pronto.
    Verifica e loga o status das conexões essenciais no terminal do worker.
    """
    print("\n--- [Worker Celery] Verificando conexões na inicialização ---")
    with sender.app.app_context():
        # 1. Teste de conexão com o Redis
        try:
            sender.app.redis_client.ping()
            print("✅ [Worker Celery] Conexão com o Redis (db=0) estabelecida com sucesso.")
        except Exception as e:
            print(f"❌ [Worker Celery] ERRO: Falha ao conectar ao Redis (db=0): {e}")

        # 2. Teste de conexão com o Broker
        try:
            with sender.app.broker_connection() as conn:
                conn.ensure_connection(max_retries=1)
            print("✅ [Worker Celery] Conexão com o Broker (Fila) estabelecida com sucesso.")
        except Exception as e:
            print(f"❌ [Worker Celery] ERRO: Falha ao conectar ao Broker: {e}")
    print("--- [Worker Celery] Pronto para receber tarefas. ---\n")

#-----------------------------------------------------------------------
# BLOCO DE DECORATORS E FUNÇÕES DE SEGURANÇA
#-----------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        if session.get('password_reset_required', False) and request.endpoint not in ['change_password_page', 'static', 'logout']:
            return redirect(url_for('change_password_page'))
        return f(*args, **kwargs)
    return decorated_function

# Registra o Blueprint na aplicação principal
app.register_blueprint(agents.agents_bp)

#-----------------------------------------------------------------------
# BLOCO DE SEGURANÇA (LOGS, BLOQUEIO, ETC.)
#-----------------------------------------------------------------------
request_log = deque(maxlen=100)
BLOCK_DURATIONS = [3600] # 1 hora para o primeiro bloqueio

def get_remote_address():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()

@app.after_request
def log_request(response):
    ip = get_remote_address()
    try:
        dns = socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        dns = "N/A"
    request_log.appendleft({
        "ip": ip, "dns": dns, "path": request.path,
        "status_code": response.status_code, "timestamp": int(time.time())
    })
    return response

def security_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = get_remote_address()
        if app.redis_client.exists(f"blocked:{ip}"):
            return jsonify({"error": "IP temporariamente bloqueado."}), 429
        return f(*args, **kwargs)
    return decorated_function

def record_failed_attempt(ip):
    """Registra uma tentativa de login falha no Redis."""
    key = f"failed:{ip}"
    # Adiciona a tentativa atual com um score de timestamp
    now = int(time.time())
    app.redis_client.zadd(key, {now: now})
    # Remove tentativas antigas (fora da janela de 5 minutos)
    app.redis_client.zremrangebyscore(key, '-inf', now - FAILED_ATTEMPT_WINDOW)
    # Define um TTL para a chave, para que ela expire se não houver mais falhas
    app.redis_client.expire(key, FAILED_ATTEMPT_WINDOW)

    # Se o número de tentativas exceder o limite, bloqueia o IP
    if app.redis_client.zcard(key) >= MAX_FAILED_ATTEMPTS:
        block_duration = BLOCK_DURATIONS[0]
        app.redis_client.set(f"blocked:{ip}", 'level_1', ex=block_duration)
        app.redis_client.delete(key) # Limpa as tentativas falhas após bloquear

#-----------------------------------------------------------------------
# ROTAS DE AUTENTICAÇÃO E GERENCIAMENTO DE USUÁRIOS
#-----------------------------------------------------------------------
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html', error_modal=None)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'success')
    return redirect(url_for('login_page'))

@app.route('/change-password', methods=['GET', 'POST'])
def change_password_page():
    if 'logged_in' not in session:
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or new_password != confirm_password:
            flash('As senhas não conferem ou estão em branco.', 'danger')
            return redirect(url_for('change_password_page'))

        hashed_password = generate_password_hash(new_password)
        db = get_db()
        db.execute("UPDATE user SET password = ?, password_reset_required = ? WHERE id = ?",
                   (hashed_password, False, session['user_id']))
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
# ROTAS DA API PRINCIPAL
#-----------------------------------------------------------------------
@app.route('/api/login', methods=['POST'])
@security_check
def api_login():
    ip = get_remote_address()

    # Torna a rota mais robusta, aceitando JSON ou dados de formulário
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Usuário e senha são obrigatórios."}), 400

    user = get_user_by_username(username)

    if user and check_password_hash(user['password'], password):
        app.redis_client.delete(f"failed:{ip}") # Limpa o contador de falhas em caso de sucesso

        session.clear()
        session['logged_in'] = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['password_reset_required'] = user['password_reset_required']

        redirect_url = url_for('change_password_page') if user['password_reset_required'] else url_for('dashboard')
        return jsonify({"success": True, "redirect_url": redirect_url})
    else:
        record_failed_attempt(ip)
        return jsonify({"error": "Credenciais inválidas."}), 401

@app.route('/api/users', methods=['POST'])
@login_required
def add_user():
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({"error": "Nome de usuário é obrigatório."}), 400

    if get_user_by_username(username) is not None:
        return jsonify({"error": "Este nome de usuário já existe."}), 409

    # Gera uma senha temporária forte e aleatória
    alphabet = string.ascii_letters + string.digits
    temporary_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    hashed_password = generate_password_hash(temporary_password)

    db = get_db()
    db.execute(
        "INSERT INTO user (username, password, password_reset_required) VALUES (?, ?, ?)",
        (username, hashed_password, True)
    )
    db.commit()
    return jsonify({
        "success": True,
        "message": f"Usuário {username} criado com sucesso.",
        "temporary_password": temporary_password
    }), 201

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Deleta um usuário."""
    # Impede que o usuário logado se delete
    if 'user_id' in session and session['user_id'] == user_id:
        return jsonify({"error": "Você não pode excluir sua própria conta."}), 403

    delete_user_by_id(user_id)
    return jsonify({"success": True, "message": "Usuário excluído com sucesso."})

@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Reseta a senha de um usuário para uma nova senha temporária."""
    # Gera uma nova senha temporária forte e aleatória
    alphabet = string.ascii_letters + string.digits
    temporary_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    hashed_password = generate_password_hash(temporary_password)

    db = get_db()
    db.execute(
        "UPDATE user SET password = ?, password_reset_required = ? WHERE id = ?",
        (hashed_password, True, user_id)
    )
    db.commit()

    return jsonify({
        "success": True,
        "message": "Senha resetada com sucesso.",
        "temporary_password": temporary_password
    })

@app.route('/api/system_stats')
@login_required
def system_stats():
    return jsonify({
        'cpu': psutil.cpu_percent(interval=None),
        'memory': psutil.virtual_memory().percent
    })

#-----------------------------------------------------------------------
# ROTAS DO PAINEL
#-----------------------------------------------------------------------

def create_admin_user_if_not_exists():
    """Cria o usuário administrador padrão se ele não existir."""
    admin_username = os.getenv('DEFAULT_ADMIN_USER', 'admin')
    if get_user_by_username(admin_username) is None:
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'changeme')
        hashed_password = generate_password_hash(admin_password)
        db = get_db()
        db.execute("INSERT INTO user (username, password, password_reset_required) VALUES (?, ?, ?)", (admin_username, hashed_password, True))
        db.commit()

@app.route('/dashboard')
@login_required
def dashboard():
    # --- Coleta de dados para os gráficos ---

    # 1. Contagem de status das requisições
    status_codes = [log['status_code'] for log in request_log]
    status_counts = {
        '2xx': len([s for s in status_codes if 200 <= s < 300]),
        '3xx': len([s for s in status_codes if 300 <= s < 400]),
        '4xx': len([s for s in status_codes if 400 <= s < 500]),
        '5xx': len([s for s in status_codes if 500 <= s < 600]),
    }

    # 2. Contagem de segurança
    blocked_count = len(app.redis_client.keys("blocked:*"))
    failed_count = len(app.redis_client.keys("failed:*"))
    security_counts = {"blocked": blocked_count, "failed": failed_count}

    # 3. Tendência de acessos (requisições por minuto nos últimos 5 minutos)
    now = int(time.time())
    access_trend = Counter()
    for i in range(5):
        minute_start = now - (i * 60)
        minute_label = time.strftime('%H:%M', time.localtime(minute_start))
        count = sum(1 for log in request_log if minute_start - 60 < log['timestamp'] <= minute_start)
        access_trend[minute_label] = count

        # 4. Ranking de agentes mais requisitados (Top 5)
        agent_ranking_raw = app.redis_client.zrevrange(
            'agent_requests:ranking', 0, 4, withscores=True
        )
        agent_ranking = {
            (agent.decode('utf-8') if isinstance(agent, bytes) else str(agent)): int(score)
            for agent, score in agent_ranking_raw
        }

        # 5. Tarefas mais lentas (Top 5)
        slowest_tasks_raw = app.redis_client.zrevrange(
            'task_execution_time', 0, 4, withscores=True
        )
        slowest_tasks = {
            (task.decode('utf-8') if isinstance(task, bytes) else str(task)): round(float(score), 2)
            for task, score in slowest_tasks_raw
        }

        return render_template(
            'dashboard.html',
            status_counts=status_counts,
            security_counts=security_counts,
            access_trend=dict(reversed(access_trend.items())),  # Ordena do mais antigo para o mais novo
            agent_ranking=agent_ranking,
            slowest_tasks=slowest_tasks
        )

@app.route('/queue-status')
@login_required
def queue_status_page():
    """Renderiza a página de status da fila."""
    queue_data = get_queue_info()
    return render_template('fila.html', queue_data=queue_data)

@app.route('/monitoring')
@login_required
def monitoring():
    # Busca IPs bloqueados e suas informações no Redis
    blocked_keys = app.redis_client.keys("blocked:*")
    blocked_ips_data = {}
    for key in blocked_keys:
        ip = key.split(":")[1]
        blocked_ips_data[ip] = {
            "level": app.redis_client.get(key),
            "expires_in": app.redis_client.ttl(key)
        }

    # Busca tentativas falhas no Redis
    failed_keys = app.redis_client.keys("failed:*")
    failed_attempts_data = {key.split(":")[1]: {"count": app.redis_client.zcard(key)} for key in failed_keys}

    return render_template('monitoring.html',
                           request_log=list(request_log),
                           blocked_ips=blocked_ips_data,
                           failed_attempts=failed_attempts_data,
                           time=time) # Passa o módulo time para o template

@app.route('/monitoring/unblock/<ip>')
@login_required
def unblock_ip(ip):
    app.redis_client.delete(f"blocked:{ip}")
    return redirect(url_for('monitoring'))

@app.route('/agents')
@login_required
def agents_page():
    """Renderiza a página de interação com os agentes."""
    return render_template('agents.html')

#-----------------------------------------------------------------------
# Gerenciamento de site
#-----------------------------------------------------------------------
@app.route('/')
def index():
    '''
    informa como a rota "/" deve agir
    informação puxada do .env
    cada retorno informa qual pagina principal deve seguir
    :return:
    '''
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
    # Verifica se o arquivo existe antes de servir
    return send_from_directory('site/html', f"{nome_pagina}.html")


#-----------------------------------------------------------------------
# COMANDOS CLI PARA GERENCIAMENTO
#-----------------------------------------------------------------------
@app.cli.command("init-app")
def init_app_command():
    """Inicializa o banco de dados e os serviços externos."""
    with app.app_context():
        init_db()
        migrate_db()
        create_admin_user_if_not_exists()
        print("Banco de dados e usuário admin inicializados.")

        # --- Verificação de Conexões ---
        print("\n--- Verificando conexões externas ---")
        # 1. Teste de conexão com o Redis (para segurança, métricas, etc.)
        try:
            app.redis_client.ping()
            print("✅ Conexão com o Redis (db=0) estabelecida com sucesso.")
        except redis.exceptions.ConnectionError as e:
            print(f"❌ ERRO: Falha ao conectar ao Redis (db=0): {e}")

        # 2. Teste de conexão com o Broker do Celery
        try:
            with celery.broker_connection() as connection:
                connection.ensure_connection(max_retries=1)
            print("✅ Conexão com o Broker Celery (Redis db=0) estabelecida com sucesso.")
        except Exception as e:
            print(f"❌ ERRO: Falha ao conectar ao Broker Celery: {e}")

    # Inicializa o modelo Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        agents.model = genai.GenerativeModel('gemini-pro')
        print("API do Gemini configurada com sucesso.")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao configurar a API do Gemini: {e}")

#-----------------------------------------------------------------------
# ENTRADA PRINCIPAL DA APLICAÇÃO (PARA DESENVOLVIMENTO)
#-----------------------------------------------------------------------
if __name__ == '__main__':
    # O comando 'flask run' já lida com o contexto da aplicação.
    # Para rodar com 'python app.py', o contexto precisa ser explícito.
    # Nota: O comando 'init-app' não será re-executado pelo reloader do modo debug.
    with app.app_context():
        init_app_command()
    app.run(host='0.0.0.0', port=5000, debug=True)
