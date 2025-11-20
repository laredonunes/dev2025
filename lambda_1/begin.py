import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


def carregar_variaveis_ambiente() -> None:
    """
    Carrega o arquivo .env a partir da raiz do projeto (um nível acima de /lambda_1)
    e valida a existência da variável GEMINI_API_KEY.
    """
    # Caminho para o .env na raiz do projeto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dotenv_path = os.path.join(base_dir, ".env")

    # Carrega o .env, se existir
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "A variável de ambiente 'GEMINI_API_KEY' não está definida.\n"
            "Defina-a no arquivo .env na raiz do projeto ou exporte-a no ambiente antes de executar.\n"
            "Exemplo no .env:\n"
            "    GEMINI_API_KEY=seu_token_aqui"
        )


def criar_cliente_genai() -> genai.Client:
    """
    Garante que as variáveis de ambiente estejam carregadas
    e devolve um cliente configurado do Google GenAI.
    """
    carregar_variaveis_ambiente()
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def gerar_resposta(texto: str, modelo: str = "gemini-flash-lite-latest") -> str:
    """
    Recebe um texto de entrada e retorna a resposta do modelo Gemini
    como string (sem imprimir na tela).

    :param texto: Texto enviado ao modelo.
    :param modelo: Nome do modelo do Gemini a ser utilizado.
    :return: Texto de resposta gerado pelo modelo.
    """
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("O parâmetro 'texto' deve ser uma string não vazia.")

    client = criar_cliente_genai()

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=texto)],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        thinkingConfig={
            "thinkingBudget": 0,
        },
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_ONLY_HIGH",  # Block few
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_ONLY_HIGH",  # Block few
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_ONLY_HIGH",  # Block few
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH",  # Block few
            ),
        ],
    )

    # Usa streaming, mas acumula em uma string de resposta
    resposta = []
    for chunk in client.models.generate_content_stream(
        model=modelo,
        contents=contents,
        config=generate_content_config,
    ):
        if getattr(chunk, "text", None):
            resposta.append(chunk.text)

    return "".join(resposta).strip()


def generate():
    """
    Mantida por compatibilidade: usa gerar_resposta com um texto fixo
    e imprime o resultado.
    """
    texto = "INSERT_INPUT_HERE"
    resposta = gerar_resposta(texto)
    print(resposta)


if __name__ == "__main__":
    # Exemplo rápido de uso direto pelo terminal
    pergunta = input("Digite sua pergunta para o Gemini: ")
    print("\nResposta:")
    print(gerar_resposta(pergunta))