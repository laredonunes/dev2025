import time

def processar_relatorio(payload: dict):
    """
    Função de exemplo que simula o processamento de um relatório.
    """
    id_relatorio = payload.get("id_relatorio", "N/A")
    print(f"✅ [Função] Iniciando processamento do relatório: {id_relatorio}")
    # Simula um trabalho demorado
    time.sleep(5) 
    print(f"✔️ [Função] Relatório {id_relatorio} processado com sucesso.")
    return {"status": "concluido", "relatorio_id": id_relatorio}

def enviar_notificacao(payload: dict):
    """
    Função de exemplo que simula o envio de uma notificação.
    """
    usuario = payload.get("usuario", "desconhecido")
    mensagem = payload.get("mensagem", "")
    print(f"✅ [Função] Enviando notificação para '{usuario}': '{mensagem}'")
    # Simula o envio
    time.sleep(1)
    print(f"✔️ [Função] Notificação para '{usuario}' enviada.")
    return {"status": "enviado", "destinatario": usuario}

def funcao_nao_encontrada(payload: dict):
    """
    Função de fallback chamada quando a ação solicitada não existe.
    """
    action = payload.get("original_action", "desconhecida")
    print(f"❌ [Função] Ação '{action}' não foi encontrada no dispatcher.")
    return {"status": "erro", "detalhe": f"Ação '{action}' não implementada."}
