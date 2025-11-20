import google.generativeai as genai
from flask import Blueprint, render_template, request, jsonify, current_app, url_for, session, redirect
import os
from lambda_1 import agente_geral
from .tasks import process_agent_request
from celery.result import AsyncResult
from functools import wraps
import uuid
from datetime import datetime, timezone
import threading
import time
from lambda_1.puxa_fila import puxa_fila
import json
from lambda_1.addfilahabbt import (adicionar_na_fila, ler_da_fila)
from lambda_1.puxa_fila import read_reds, read_status

# Cria o Blueprint
agents_bp = Blueprint(
    'agents', 
    __name__,
    template_folder='templates',
    static_folder='static'
)

#===============================================|
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', '16379')
import redis
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    r.ping()
    print("Conectado ao Redis com sucesso!")
except redis.exceptions.ConnectionError as e:
    print(f"Erro ao conectar ao Redis: {e}")
    # Se não puder conectar, saia ou trate o erro
    exit(1)


# --- 2. A Função da Fila ---
def adicionar_item_fila(redis_conn, nome_da_fila: str, item: str):
    """
    Adiciona um item ao FINAL (lado direito) de uma lista no Redis.
    Se a lista não existir, ela é criada.

    Args:
        redis_conn: A conexão ativa do Redis.
        nome_da_fila: A chave do Redis que será usada como fila.
        item: A string (ou JSON) que você quer adicionar à fila.
    """
    try:
        # RPUSH = Right Push (Empurrar pela Direita)
        # Adiciona o item ao final da lista (cauda da fila)
        tamanho_atual = redis_conn.rpush(nome_da_fila, item)

        print(f"Item '{item}' adicionado à fila '{nome_da_fila}'.")
        print(f"Tamanho atual da fila: {tamanho_atual}")

    except redis.exceptions.RedisError as e:
        print(f"Erro ao adicionar item na fila: {e}")


class TaskManager:
    """
    Gerencia uma única tarefa de fundo, garantindo que ela não seja
    executada em duplicidade se já estiver ativa.
    """

    def __init__(self, task_function):
        # A função que realmente será executada (ex: puxa_fila)
        self.task_function = task_function
        self._lock = threading.Lock()
        self._task_thread = None

    def _background_wrapper(self):
        """Wrapper interno que chama a sua função."""
        print(f"INÍCIO: Executando '{self.task_function.__name__}' em fundo...")
        try:
            # Chama a função que você passou (puxa_fila)
            self.task_function()
        except Exception as e:
            print(f"ERRO na tarefa '{self.task_function.__name__}': {e}")
        finally:
            print(f"FIM: Tarefa '{self.task_function.__name__}' terminada.")

    def run_task(self):
        """
        Esta é a função que você chamará.
        Ela inicia a tarefa de fundo APENAS se ela não estiver rodando.
        """
        print(f"\n[CHAMADA] 'run_task' foi chamada.")

        with self._lock:
            if self._task_thread and self._task_thread.is_alive():
                print("[INFO] A tarefa já está em execução. Ignorando esta chamada.")
                return

            print("[AÇÃO] Nenhuma tarefa ativa. Iniciando uma nova...")
            # O 'target' agora é o nosso wrapper
            self._task_thread = threading.Thread(target=self._background_wrapper)
            self._task_thread.start()



#====================================================================|
# O modelo será inicializado no app principal para garantir que o .env seja carregado primeiro.
model = None

# Decorator para verificar se a API está configurada
def gemini_api_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Acessa o modelo global do módulo
        global model
        if model is None:
            return jsonify({"error": "A API do Gemini não está configurada corretamente. Verifique a GEMINI_API_KEY."}), 503
        return f(*args, **kwargs)
    return decorated_function

def rate_limit_agent_api(f):
    """
    Decorator para limitar a frequência de requisições à API do agente.
    Impede que um mesmo IP faça múltiplas requisições em um curto período.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Pega o IP do cliente
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()
        cooldown = current_app.config.get('AGENT_API_COOLDOWN_SECONDS', 15)

        # Cria uma chave única no Redis para o rate limit deste IP
        rate_limit_key = f"rate_limit:agent_api:{ip}"

        # Tenta definir a chave. Se a chave já existir (nx=True), o comando falha.
        if not current_app.redis_client.set(rate_limit_key, 1, ex=cooldown, nx=True):
            ttl = current_app.redis_client.ttl(rate_limit_key)
            return jsonify({"error": f"Muitas requisições. Por favor, aguarde {ttl} segundos."}), 429
        return f(*args, **kwargs)
    return decorated_function

#-----------------------------------------------------------------------
# ROTAS DO BLUEPRINT DE AGENTES
#-----------------------------------------------------------------------


@agents_bp.route('/api/agents/ask', methods=['POST'])
@gemini_api_required
def ask_agent():
    """
    Recebe uma pergunta, invoca a lambda_1 'agente_geral' de forma síncrona
    e retorna a resposta do Gemini. Útil para testes rápidos.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Corpo da requisição deve ser um JSON válido."}), 400

    question = data.get('question')
    system_prompt = data.get('system_prompt', 'Você é um assistente prestativo.')

    if not question:
        return jsonify({"error": "Nenhuma pergunta foi fornecida."}), 400

    try:
        # Monta o payload e chama a função 'executar' da lambda_1 diretamente
        payload = {"question": question, "system_prompt": system_prompt}
        answer = agente_geral.executar(payload)
        return jsonify({"answer": answer})
    except Exception as e:
        # Log do erro no servidor para depuração
        current_app.logger.error(f"Erro na chamada síncrona do agente: {e}", exc_info=True)
        return jsonify({"error": "Ocorreu um erro ao processar sua pergunta."}), 500

#-----------------------------------------------------------------------
# ROTAS ASSÍNCRONAS COM CELERY
#-----------------------------------------------------------------------

@agents_bp.route('/api/agents/ask-async', methods=['POST'])
@rate_limit_agent_api
def ask_agent_async():
    """
    Recebe uma pergunta, enfileira a tarefa e retorna o ID da tarefa.
    """
    if not request.is_json:
        return jsonify({"error": "Requisição deve ser do tipo application/json"}), 415

    data = request.get_json()
    question = data.get('question')
    # Recebe o nome do agente e o prompt do sistema do frontend
    agent_name = data.get('agent_name', 'geral')
    acao = data.get('acao', 'processar_mensagem')
    system_prompt = data.get('system_prompt', 'Você é um assistente prestativo.')
    usuario = data.get('usuario', '')

    if not question:
        return jsonify({"error": "Nenhuma pergunta foi fornecida."}), 400

    # Monta o dicionário/envelope da mensagem
    message = {
        "agent_name": agent_name,
        "payload": {
            "question": question,
            "system_prompt": system_prompt
        },
        "metadata": {
            "user_id": usuario,
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": str(uuid.uuid4())
        }
    }
    print(message)
    # --- Instrumentação ---
    # Incrementa o contador de requisições para este agente no Redis
    current_app.redis_client.zincrby('agent_requests:ranking', 1, message['agent_name'])
    # Dispara a tarefa assíncrona
    task = process_agent_request.delay(message)
    #print(f'taskid:{task.id}')
    message["task.id"] = task.id
    #current_app.logger.info(f"Tarefa {task.id} enviada para a fila do Celery.")

    #string_json = json.dumps(message, indent=4)
    #adicionar_item_fila(r, "agente_geral", string_json)

    #---------------------------------|
    adicionar_na_fila(action=acao, payload=message, QUEUE_NAME=message['agent_name'])
    #---------------------------------|

    #---------------------------------|

    # 1. Crie uma instância do gerenciador
    #    E PASSE sua função para ele.
    #manager = TaskManager(task_function=puxa_fila)
    # 2. Primeira chamada: Deve iniciar o puxa_fila
    #manager.run_task()

    # Retorna o ID da tarefa e uma URL para consultar o status
    return jsonify({
        "task_id": task.id,
        "trace_id": message["metadata"]["trace_id"], # Retorna o trace_id para o cliente
        "status_url": url_for('agents.get_task_status', task_id=task.id, _external=True)
    }), 202 # HTTP 202 Accepted


@agents_bp.route('/api/agents/status/<string:task_id>', methods=['GET'])
def get_task_status(task_id):
    """Consulta o status e o resultado de uma tarefa."""
    task_result = AsyncResult(task_id)
    if read_status(task_id):
        return jsonify({
            "status": "SUCCESS",
            # O resultado fica aqui, com a expiração padrão do Celery ou a que configurarmos
            "answer": read_reds(task_id)
        })
    else:
        return jsonify({"status": "PENDING"}), 202

    '''
    @agents_bp.route('/api/agents/status/<string:task_id>', methods=['GET'])
def get_task_status(task_id):
    """Consulta o status e o resultado de uma tarefa."""
    task_result = AsyncResult(task_id)
    if task_result.ready():
        if task_result.successful():
            return jsonify({
                "status": "SUCCESS",
                # O resultado fica aqui, com a expiração padrão do Celery ou a que configurarmos
                "answer": task_result.get()
            })
        else:
            return jsonify({"status": "FAILURE", "error": str(task_result.info)}), 500
    else:
        return jsonify({"status": "PENDING"}), 202
    
    '''
