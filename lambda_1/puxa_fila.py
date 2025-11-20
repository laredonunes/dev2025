import json
import time
import os
from lambda_1.begin import gerar_resposta

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


# A 'fila_de_itens' deve vir como um argumento da função
# (importações e conexão 'r' vêm antes)

# A 'fila_de_itens' deve vir como um argumento da função
def armazenar_informacao(redis_conn, chave: str, valor):
    """
    Armazena uma informação (valor) no Redis sob uma chave específica.

    Args:
        redis_conn: A conexão ativa do Redis.
        chave: O nome da "etiqueta" onde você quer guardar o dado (ex: "user:100:profile").
        valor: O dado que você quer guardar. Pode ser uma string, int, ou
               um dicionário (que será convertido para JSON).
    """
    try:
        # Se o valor for um dicionário ou lista, converte para JSON
        if isinstance(valor, (dict, list)):
            valor_para_armazenar = json.dumps(valor)
        else:
            valor_para_armazenar = valor

        # Usa o comando SET para salvar o dado
        redis_conn.set(chave, valor_para_armazenar)

        print(f"Sucesso: Informação salva na chave '{chave}'.")

    except redis.exceptions.RedisError as e:
        print(f"Erro ao armazenar informação no Redis: {e}")
    except TypeError as e:
        print(f"Erro ao converter o valor para JSON: {e}")

def puxa_fila():
    """
    Esta função lê a fila item por item e chama outra função.
    Ela processará a fila ATÉ ELA FICAR VAZIA.
    """
    nome_da_fila = "agente_geral"

    print(f"... (puxa_fila) Aguardando itens na fila '{nome_da_fila}'...")

    while True:
        item_json_str = None  # Renomeado (não é mais bytes)
        item_dicionario = None
        try:
            # 1. BLPOP agora retorna uma string, graças a decode_responses=True
            #    A variável 'item_json_str' já contém a string JSON
            _, item_json_str = r.blpop(nome_da_fila, timeout=0)

            # 2. A linha ".decode('utf-8')" foi REMOVIDA.
            #    Vamos direto para o json.loads()

            # 3. Converte de JSON (string) para dicionário
            item_dicionario = json.loads(item_json_str)

        except redis.exceptions.RedisError as e:
            # Se o Redis cair, espera 5s e tenta reconectar
            print(f"... (puxa_fila) Erro de conexão com Redis: {e}. Tentando novamente em 5s...")
            time.sleep(5)
            continue  # Volta ao início do loop 'while'

        except json.JSONDecodeError:
            print(f"... (puxa_fila) ERRO: O item '{item_json_str}' não é um JSON válido. Pulando.")
            continue  # Pega o próximo item

        except Exception as e:
            # Pega outros erros inesperados
            print(f"Erro inesperado no 'puxa_fila': {e}")
            time.sleep(1)
            continue

        # 4. Se tudo deu certo, processa o item
        if item_dicionario:
            print(f"... (puxa_fila) Pegou item da fila: {item_dicionario}")
            print('-'*90)
            data = item_dicionario["payload"]
            #print(item_dicionario["task.id"])
            fila_ret = item_dicionario["task.id"]
            pronpt = data.get("question", "")
            if pronpt != "":
                ret = gerar_resposta(pronpt)
                armazenar_informacao(r, fila_ret, ret)


            # processa_item(item_dicionario)

def ler_informacao(redis_conn, chave: str):
    """
    Lê uma informação armazenada no Redis sob uma chave específica.

    Args:
        redis_conn: A conexão ativa do Redis.
        chave: O nome da chave onde o dado está armazenado.

    Returns:
        O valor armazenado na chave, convertido de volta para o tipo original (dict, list, str, int, etc.).
        Retorna None se a chave não existir ou em caso de erro.
    """
    try:
        # Recupera o valor da chave
        valor_redis = redis_conn.get(chave)

        if valor_redis is None:
            print(f"Aviso: A chave '{chave}' não existe ou expirou.")
            return None

        # Tenta converter de JSON, se possível
        try:
            valor_convertido = json.loads(valor_redis)
            return valor_convertido
        except json.JSONDecodeError:
            # Se não for JSON, retorna como string ou número
            try:
                return int(valor_redis)
            except ValueError:
                try:
                    return float(valor_redis)
                except ValueError:
                    return valor_redis

    except redis.exceptions.RedisError as e:
        print(f"Erro ao ler informação do Redis: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao ler informação: {e}")
        return None


def read_reds(key):
    st = ler_informacao(r, key)
    return st

def read_status(key):
    st = ler_informacao(r, key)
    if st == "":
        return False
    return True