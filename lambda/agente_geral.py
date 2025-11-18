import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- Otimização: Inicializar o modelo uma vez por processo do worker ---
# Esta parte será executada quando o módulo for importado pela primeira vez pelo worker.
model = None
try:
    # Garante que a chave de API seja carregada
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada no ambiente.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    print("Lambda 'agente_geral': Modelo Gemini inicializado com sucesso.")
except Exception as e:
    # O log do current_app não está disponível aqui, então um print é um fallback
    print(f"ERRO CRÍTICO na Lambda 'agente_geral': Falha ao inicializar o modelo Gemini: {e}")


def executar(payload: dict) -> str:
    """
    Executa a lógica do agente "geral".
    Recebe um payload e retorna a resposta do Gemini.
    """
    if model is None:
        raise RuntimeError("Lambda 'agente_geral': Modelo Gemini não está disponível.")

    question = payload.get("question")
    if not question:
        raise ValueError("O 'payload' da mensagem para o agente_geral não contém uma 'question'.")

    # A captura de exceção da chamada `generate_content` será feita pela tarefa Celery.
    response = model.generate_content(question)
    return response.text