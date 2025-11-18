import redis
import os
import json

def get_queue_info() -> dict:
    """
    Conecta-se ao Redis (broker do Celery) para inspecionar as filas ativas
    e listar os IDs das tarefas pendentes.

    Retorna um dicionário onde as chaves são os nomes das filas e os valores
    são listas de dicionários de tarefas.
    """
    try:
        # Conecta-se ao mesmo Redis que o Celery usa como BROKER (db=0 por padrão)
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '16379')
        # Usamos decode_responses=False porque os dados da fila do Celery são bytes
        r = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=False)

        # Por padrão, a fila principal do Celery se chama 'celery'
        # Em um sistema mais complexo, poderíamos escanear por chaves de fila
        queues_to_check = ['celery']
        
        all_queues_data = {}

        for queue_name in queues_to_check:
            # Pega todas as tarefas da lista do Redis (LRANGE 0 -1)
            raw_tasks = r.lrange(queue_name, 0, -1)
            tasks_info = []
            for raw_task in raw_tasks:
                # A mensagem da tarefa é um JSON, vamos decodificá-lo
                task_message = json.loads(raw_task.decode('utf-8'))
                tasks_info.append({"task_id": task_message['headers']['id']})
            all_queues_data[queue_name] = tasks_info
        
        return all_queues_data
    except Exception as e:
        print(f"Erro ao conectar ao Redis para inspecionar filas: {e}")
        return {"error": str(e)}