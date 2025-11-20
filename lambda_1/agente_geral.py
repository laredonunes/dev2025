import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

# --- Inicialização ---
# CORREÇÃO: O estado inicial deve ser 'None' para que a verificação 'is None' funcione
# corretamente antes da inicialização.
flash_model = None

CLASSIFICATION_PROMPT = """
Você é um sistema de roteamento de IA para um jogo chamado ECO QUEST. Sua tarefa é analisar a pergunta de um usuário e classificá-la em duas dimensões: complexidade e agente de destino.

Dimensões:
1.  **Complexidade**:
    -   "simples": A pergunta pode ser respondida diretamente com uma única interação.
    -   "complexa": A pergunta requer análise, avaliação de contexto de um jogo, ou múltiplos passos.

2.  **Agente de Destino**:
    -   "orientador": A pergunta é uma solicitação de ajuda ou dica.
    -   "avaliador": A pergunta é uma proposta ou solução que precisa ser avaliada.
    -   "adaptador": A pergunta indica que o usuário está travado ou frustrado.
    -   "geral": Para todas as outras perguntas.

Responda APENAS com um objeto JSON contendo as chaves "complexidade" e "agente_destino".
"""


def inicializar_modelo():
    """Função separada para inicializar o modelo global."""
    global flash_model
    try:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no ambiente.")

        genai.configure(api_key=api_key)
        flash_model = genai.GenerativeModel('gemini-1.5-flash')
        print("Modelo 'gemini-1.5-flash' inicializado com sucesso.")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao inicializar o modelo Gemini: {e}")
        flash_model = None


def executar(message: dict) -> dict:
    """
    Executa a lógica do agente "geral", que atua como um roteador.
    """

    # --- CORREÇÃO: A validação da entrada (payload) deve vir ANTES da verificação do modelo ---

    # 1. Extrair e validar a entrada primeiro (Lógica Fail-Fast)
    payload = message.get("payload", {})
    metadata = message.get("metadata", {})
    question = payload.get("question")

    if not question:
        raise ValueError("O 'payload' da mensagem para o agente_geral não contém uma 'question'.")

    # 2. Agora, verificar o estado do modelo
    if flash_model is None:
        print("❌ [agente_geral] Erro: Tentativa de execução sem o modelo Gemini Flash inicializado.")
        raise RuntimeError("Lambda 'agente_geral': Modelo Gemini Flash não está disponível.")

    # Se passamos pelas validações, continuamos
    print(f"✅ [agente_geral] Lambda iniciada (Trace ID: {metadata.get('trace_id')}). Pergunta: '{question[:50]}...'")

    # 1. Classificar a pergunta
    print("   - [agente_geral] Etapa 1: Classificando a pergunta...")
    classification_response = flash_model.generate_content(
        f"{CLASSIFICATION_PROMPT}\n\nPergunta do Usuário: \"{question}\""
    )

    try:
        classification = json.loads(classification_response.text)
        print(f"   - [agente_geral] Classificação recebida: {classification}")
    except json.JSONDecodeError:
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
        print(
            "   - [agente_geral] Etapa 2: Pergunta classificada como 'complexa'. Nenhuma resposta direta será gerada.")

    # 3. Montar o dicionário de contexto
    print("   - [agente_geral] Etapa 3: Montando dicionário de contexto final...")
    context_dict = {
        "original_question": question,
        "classification": classification,
        "answer": answer,
        "next_agent": classification.get("agente_destino"),
        "status": "PROCESSED"
    }

    print("✅ [agente_geral] Lambda concluída. Retornando contexto.")
    return context_dict