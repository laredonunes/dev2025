from celery import shared_task
from flask import current_app
import importlib
import time

@shared_task(bind=True)
def process_agent_request(self, message: dict) -> str:
    """
    Tarefa Celery que atua como um dispatcher.
    Ela lê o 'agent_name' da mensagem, importa a "lambda" correspondente
    do diretório /lambda e a executa.
    """
    agent_name = message.get("agent_name", "desconhecido")
    payload = message.get("payload", {})
    metadata = message.get("metadata", {})

    current_app.logger.info(
        f"Dispatcher Celery (Task ID: {self.request.id}):\n"
        f"  - Agente: '{agent_name}'\n"
        f"  - Trace ID: {metadata.get('trace_id')}"
    )

    start_time = time.time()

    try:
        # Importa dinamicamente o módulo do agente a partir da pasta 'lambda'
        # Ex: agent_name='agente_geral' -> import lambda_1.agente_geral
        agent_module = importlib.import_module(f"lambda_1.{agent_name}")
        
        current_app.logger.info(f"Tarefa {self.request.id}: Executando lambda '{agent_name}'...")
        
        # Chama a função 'executar' dentro do módulo do agente
        result = agent_module.executar(message) # Passa a mensagem completa para a lambda
        
        # --- Instrumentação ---
        execution_time = time.time() - start_time
        # Adiciona o tempo de execução a um sorted set no Redis
        current_app.redis_client.zadd('task_execution_time', {self.request.id: execution_time})
        # Mantém apenas as 100 tarefas mais lentas para não encher a memória
        current_app.redis_client.zremrangebyrank('task_execution_time', 0, -101)

        current_app.logger.info(f"Tarefa {self.request.id}: Lambda '{agent_name}' executada com sucesso.")
        return result

    except Exception as e:
        current_app.logger.error(
            f"ERRO na Tarefa {self.request.id} ao processar agente '{agent_name}': {e}",
            exc_info=True # Adiciona o traceback completo ao log
        )
        # Isso fará com que o Celery registre a tarefa como falha.
        raise