import pika
import os
import json
import time
from dotenv import load_dotenv

# Importa as funções que podem ser chamadas
from node_function import processar_relatorio, enviar_notificacao, funcao_nao_encontrada, processar_mensagem
from node_function.funcao_apoio import write_bd_5_minutos

# --- Mapeamento de Ações para Funções (Dispatcher) ---
# Este dicionário funciona como o "case" do nosso programa.
# A chave é a 'action' que esperamos na mensagem JSON.
# O valor é a função que deve ser executada.
ACTION_DISPATCHER = {
    "processar_relatorio": processar_relatorio,
    "enviar_notificacao": enviar_notificacao,
    "processar_mensagem": processar_mensagem,
}

def main():
    """
    Função principal do worker. Conecta ao RabbitMQ e despacha tarefas
    para as funções corretas com base na 'action' da mensagem.
    """
    load_dotenv()

    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
    queue_name = 'agente2'

    print("⏳ [sisMQ Worker] Tentando conectar ao RabbitMQ...")
    
    # Tenta conectar com retries, pois o RabbitMQ pode demorar a iniciar no Docker
    connection = None
    for i in range(10):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port)
            )
            print(f"✅ [sisMQ Worker] Conectado ao RabbitMQ em {rabbitmq_host}:{rabbitmq_port}.")
            break
        except pika.exceptions.AMQPConnectionError:
            print(f"   - Tentativa {i+1}/10 falhou. Tentando novamente em 5 segundos...")
            time.sleep(5)
    
    if not connection:
        print("❌ [sisMQ Worker] Não foi possível conectar ao RabbitMQ após várias tentativas. Encerrando.")
        return

    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    print(f"   - Fila '{queue_name}' declarada. Aguardando por tarefas...")

    def callback(ch, method, properties, body):
        """
        Função executada para cada mensagem recebida.
        """
        try:
            message = json.loads(body)
            action = message.get("action")
            payload = message.get("payload", {})

            print(f"\n➡️  [sisMQ Worker] Tarefa recebida. Action: '{action}'")

            # --- Lógica do "CASE" ---
            # Busca a função no dispatcher. Se não encontrar, usa a função de fallback.
            target_function = ACTION_DISPATCHER.get(action, funcao_nao_encontrada)
            
            # Adiciona a ação original ao payload para a função de fallback saber o que falhou
            if target_function == funcao_nao_encontrada:
                payload['original_action'] = action

            # Executa a função correspondente
            resultado = target_function(payload)
            
            print(f"✔️  [sisMQ Worker] Ação '{action}' concluída. Resultado: {resultado}")

        except json.JSONDecodeError:
            print("❌ [sisMQ Worker] Erro: A mensagem recebida não é um JSON válido.")
        except Exception as e:
            print(f"❌ [sisMQ Worker] Erro inesperado ao processar a tarefa: {e}")
        
        # Confirma para o RabbitMQ que a mensagem foi processada (mesmo em caso de erro)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("🛑 [sisMQ Worker] Consumo interrompido.")
        connection.close()

if __name__ == '__main__':
    main()
