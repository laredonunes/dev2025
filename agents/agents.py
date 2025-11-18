import google.generativeai as genai
from flask import Blueprint, render_template, request, jsonify, current_app, url_for, session, redirect
import os
from .tasks import process_agent_request
from celery.result import AsyncResult
from functools import wraps
import uuid
from datetime import datetime, timezone

# Cria o Blueprint
agents_bp = Blueprint(
    'agents', 
    __name__,
    template_folder='templates',
    static_folder='static'
)

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
    """Recebe uma pergunta e retorna a resposta do Gemini."""
    data = request.get_json()
    question = data.get('question')

    if not question:
        return jsonify({"error": "Nenhuma pergunta foi fornecida."}), 400

    try:
        response = model.generate_content(question)
        return jsonify({"answer": response.text})
    except Exception as e:
        # Log do erro no servidor para depuração
        current_app.logger.error(f"Erro na API do Gemini: {e}")
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

    if not question:
        return jsonify({"error": "Nenhuma pergunta foi fornecida."}), 400

    # Monta o dicionário/envelope da mensagem
    message = {
        "agent_name": "geral",
        "payload": {
            "question": question
        },
        "metadata": {
            "user_id": session.get('user_id'), # Assumindo que o user_id está na sessão
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": str(uuid.uuid4())
        }
    }

    # --- Instrumentação ---
    # Incrementa o contador de requisições para este agente no Redis
    current_app.redis_client.zincrby('agent_requests:ranking', 1, message['agent_name'])

    # Dispara a tarefa assíncrona
    task = process_agent_request.delay(message)

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
