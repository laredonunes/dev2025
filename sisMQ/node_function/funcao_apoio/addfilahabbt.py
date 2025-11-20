import pika
import os
import json
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configurações de Conexão (lidas do .env) ---
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
QUEUE_NAME = 'task_queue'  # A fila que o sisMQ está escutando

def adicionar_na_fila(action: str, payload: dict, QUEUE_NAME):
    """
    Conecta ao RabbitMQ e publica uma tarefa no formato esperado pelo sisMQ.

    :param action: A string que define qual função o sisMQ deve executar (ex: "processar_relatorio").
    :param payload: Um dicionário com os dados necessários para a função.
    """
    connection = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        # 1. Monta a mensagem no formato correto { "action": "...", "payload": {...} }
        mensagem_completa = {
            "action": action,
            "payload": payload
        }
        
        # 2. Converte a mensagem completa para JSON
        mensagem_json = json.dumps(mensagem_completa)

        # 3. Publica a mensagem
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=mensagem_json,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        print(f"✅ Tarefa '{action}' adicionada à fila '{QUEUE_NAME}'.")

    except Exception as e:
        print(f"❌ Erro ao adicionar na fila: {e}")
    finally:
        if connection and connection.is_open:
            connection.close()

def ler_da_fila(QUEUE_NAME) -> any:
    """
    Conecta ao RabbitMQ, lê uma única mensagem da fila, a converte de volta
    para seu formato original (um dicionário com 'action' e 'payload') e a remove da fila.

    :return: O dicionário da mensagem, ou None se a fila estiver vazia.
    """
    connection = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        method_frame, properties, body = channel.basic_get(queue=QUEUE_NAME, auto_ack=False)

        if method_frame is None:
            print("ℹ️ A fila está vazia. Nenhuma mensagem para ler.")
            return None

        dado_original = json.loads(body.decode('utf-8'))
        print(f"✅ Dado lido da fila: {dado_original}")

        channel.basic_ack(method_frame.delivery_tag)
        return dado_original

    except Exception as e:
        print(f"❌ Erro ao ler da fila: {e}")
        return None
    finally:
        if connection and connection.is_open:
            connection.close()

# --- Exemplo de Uso ---
if __name__ == '__main__':
    print("--- Testando o Módulo de Fila para o sisMQ ---")
    QUEUE_NAME = "fila_teste"
    # Exemplo 1: Adicionar uma tarefa de "processar_relatorio"
    print("\n1. Adicionando tarefa de relatório...")
    payload_relatorio = {"id_relatorio": "XYZ-789", "formato": "pdf"}
    adicionar_na_fila(action="processar_relatorio", payload=payload_relatorio, QUEUE_NAME=QUEUE_NAME)

    # Exemplo 2: Adicionar uma tarefa de "enviar_notificacao"
    print("\n2. Adicionando tarefa de notificação...")
    payload_notificacao = {"usuario": "Laredo", "mensagem": "Sua fatura chegou!"}
    adicionar_na_fila(action="enviar_notificacao", payload=payload_notificacao, QUEUE_NAME=QUEUE_NAME)

    # Exemplo 3: Ler o primeiro item da fila (deve ser o relatório)
    print("\n3. Lendo o primeiro item da fila...")
    dado_lido_1 = ler_da_fila(QUEUE_NAME)
    if dado_lido_1:
        print(f"   -> Conteúdo: {dado_lido_1}")
        assert dado_lido_1["action"] == "processar_relatorio"
        assert dado_lido_1["payload"] == payload_relatorio

    # Exemplo 4: Ler o segundo item da fila (deve ser a notificação)
    print("\n4. Lendo o segundo item da fila...")
    dado_lido_2 = ler_da_fila(QUEUE_NAME)
    if dado_lido_2:
        print(f"   -> Conteúdo: {dado_lido_2}")
        assert dado_lido_2["action"] == "enviar_notificacao"
        assert dado_lido_2["payload"] == payload_notificacao

    print("\n--- Teste concluído com sucesso! ---")
