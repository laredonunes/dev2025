import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

# --- Otimização: Inicializar o modelo uma vez por processo do worker ---
# Esta parte será executada quando o módulo for importado pela primeira vez pelo worker.
flash_model = None
try:
    # Garante que a chave de API seja carregada
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no ambiente.")

    genai.configure(api_key=api_key)
    # Usaremos o modelo flash, que é mais rápido e ideal para classificação e respostas simples.
    flash_model = genai.GenerativeModel('gemini-1.5-flash')
    print("Lambda 'agente_geral': Modelo 'gemini-1.5-flash' inicializado com sucesso.")
except Exception as e:
    # O log do current_app não está disponível aqui, então um print é um fallback
    print(f"ERRO CRÍTICO na Lambda 'agente_geral': Falha ao inicializar o modelo Gemini: {e}")

CLASSIFICATION_PROMPT = """
Você é um sistema de roteamento de IA para um jogo chamado ECO QUEST. Sua tarefa é analisar a pergunta de um usuário e classificá-la em duas dimensões: complexidade e agente de destino.

Dimensões:
1.  **Complexidade**:
    -   "simples": A pergunta pode ser respondida diretamente com uma única interação (ex: "Qual a capital da França?", "O que é reflorestamento?").
    -   "complexa": A pergunta requer análise, avaliação de contexto de um jogo, ou múltiplos passos para ser respondida (ex: "Minha proposta é criar drones para fiscalizar a área.", "Estou travado, o que faço agora?").

2.  **Agente de Destino**:
    -   "orientador": A pergunta é uma solicitação de ajuda, dica ou guia sobre como proceder.
    -   "avaliador": A pergunta é uma proposta, uma solução ou uma resposta a um desafio que precisa ser avaliada.
    -   "adaptador": A pergunta indica que o usuário está travado, frustrado ou a interação precisa de um ajuste de ritmo.
    -   "geral": Para todas as outras perguntas que não se encaixam nas categorias acima.

Responda APENAS com um objeto JSON contendo as chaves "complexidade" e "agente_destino".

Exemplo de Pergunta: "Minha ideia é usar eucaliptos para reflorestar mais rápido."
Sua Resposta:
{"complexidade": "complexa", "agente_destino": "avaliador"}

Exemplo de Pergunta: "O que significa 'bioremediação'?"
Sua Resposta:
{"complexidade": "simples", "agente_destino": "geral"}
"""

def executar(message: dict) -> dict:
    """
    Executa a lógica do agente "geral", que atua como um roteador.
    Classifica a pergunta e prepara um dicionário de contexto para o próximo agente.
    """
    if flash_model is None:
        print("❌ [agente_geral] Erro: Tentativa de execução sem o modelo Gemini Flash inicializado.")
        raise RuntimeError("Lambda 'agente_geral': Modelo Gemini Flash não está disponível.")

    # Extrai as informações da mensagem recebida
    payload = message.get("payload", {})
    metadata = message.get("metadata", {})
    question = payload.get("question")

    print(f"✅ [agente_geral] Lambda iniciada (Trace ID: {metadata.get('trace_id')}). Pergunta: '{question[:50]}...'")

    if not question:
        raise ValueError("O 'payload' da mensagem para o agente_geral não contém uma 'question'.")

    # 1. Classificar a pergunta usando o modelo flash
    print("   - [agente_geral] Etapa 1: Classificando a pergunta...")
    classification_response = flash_model.generate_content(f"{CLASSIFICATION_PROMPT}\n\nPergunta do Usuário: \"{question}\"")
    try:
        classification = json.loads(classification_response.text)
        print(f"   - [agente_geral] Classificação recebida: {classification}")
    except json.JSONDecodeError:
        # Fallback em caso de resposta mal formatada da IA
        print("   - [agente_geral] AVISO: A resposta da IA de classificação não era um JSON válido. Usando fallback.")
        classification = {"complexidade": "complexa", "agente_destino": "geral"}

    answer = ""
    # 2. Se a pergunta for simples, gerar uma resposta direta
    if classification.get("complexidade") == "simples":
        print("   - [agente_geral] Etapa 2: Pergunta classificada como 'simples'. Gerando resposta direta...")
        simple_answer_response = flash_model.generate_content(question)
        answer = simple_answer_response.text
        print(f"   - [agente_geral] Resposta direta gerada: '{answer[:50]}...'")
    else:
        print("   - [agente_geral] Etapa 2: Pergunta classificada como 'complexa'. Nenhuma resposta direta será gerada.")

    # 3. Montar o dicionário de contexto para o próximo passo
    print("   - [agente_gereal] Etapa 3: Montando dicionário de contexto final...")
    context_dict = {
        "original_question": question,
        "classification": classification,
        "answer": answer,
        "next_agent": classification.get("agente_destino"),
        "status": "PROCESSED"
    }

    print("✅ [agente_geral] Lambda concluída. Retornando contexto.")
    return context_dict