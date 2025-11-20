import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .funcao_apoio.puxa_fila import write_bd_5_minutos
import json


def processar_mensagem(payload: dict):
    """
    Função de exemplo que simula o processamento de um relatório.
    message = {
        "agent_name": agent_name,
        "payload": {
            "question": question,
            "system_prompt": system_prompt
        },
        "metadata": {
            "user_id": "",
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": str(uuid.uuid4())
        }
    }
    """
    message = payload
    print(message)
    agent_name = message.get("agent_name", "")
    prompt = message.get("payload", "")
    desastre = message.get("question", "voce esta analisando qualquer tragedia")
    #----------------------------------------|
    question = prompt.get("question", "")
    diretriz = prompt.get("system_prompt", "")
    #----------------------------------------|
    task_id = message.get("task.id", "")
    metadata = message.get("metadata", "")
    user_id = metadata.get("user_id", "")
    trace_id = metadata.get("trace_id", "")
    #----------------------------------------| viabilidade da mensagem
    if task_id is "" and prompt is "":
        return {"mesage": "falha dados principais nulos"}

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

    texto = {
      "contexto": {
        "tragedia_ambiental": desastre,
        "variaveis_relevantes": [
          "Impacto ecológico",
          "Fatores econômicos",
          "Limitações tecnológicas",
          "Tempo de resposta",
            "leis ambientais brasileiras",
            "normas ambientais Brasileiras",
            "atribuições de organs ambientais"
        ],
        "objetivo_educacional": "Fazer o usuário refletir sobre trade-offs e consequências"
      },
      "diretriz_do_jogo": diretriz,
      "resposta_usuario": question,
      "instrucoes_agente": [
        "Baseie a próxima pergunta na resposta do usuário e nas variáveis do contexto",
        "Introduza consequências realistas (ex.: custos, impactos colaterais)",
        "Avance a narrativa sem revelar soluções óbvias",
        "Mantenha tom envolvente como um RPG"
      ]
    }
    texto = json.dumps(texto)
    resposta = gerar_resposta(texto)
    write_bd_5_minutos(task_id, resposta)

    print(f"fila: {task_id} \nResposta gemini: {texto}")


def gerar_perguntas_multipla_escolha(payload: dict):
    """
    Gera perguntas de múltipla escolha para direcionar o jogador a ações interessantes
    """
    message = payload
    print(message)
    agent_name = message.get("agent_name", "")
    prompt = message.get("payload", "")
    desastre = message.get("question", "você está analisando qualquer tragédia")

    # ----------------------------------------|
    question = prompt.get("question", "")
    diretriz = prompt.get("system_prompt", "")
    # ----------------------------------------|
    task_id = message.get("task.id", "")
    metadata = message.get("metadata", "")
    user_id = metadata.get("user_id", "")
    trace_id = metadata.get("trace_id", "")
    # ----------------------------------------| viabilidade da mensagem
    if task_id == "" and prompt == "":
        return {"message": "falha dados principais nulos"}

    def carregar_variaveis_ambiente() -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dotenv_path = os.path.join(base_dir, ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY não encontrada")

    def criar_cliente_genai() -> genai.Client:
        carregar_variaveis_ambiente()
        api_key = os.environ.get("GEMINI_API_KEY")
        return genai.Client(api_key=api_key)

    def gerar_resposta(texto: str, modelo: str = "gemini-flash-lite-latest") -> str:
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("Texto deve ser string não vazia")

        client = criar_cliente_genai()
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=texto)])]

        generate_content_config = types.GenerateContentConfig(
            thinkingConfig={"thinkingBudget": 0},
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )

        resposta = []
        for chunk in client.models.generate_content_stream(
                model=modelo,
                contents=contents,
                config=generate_content_config,
        ):
            if getattr(chunk, "text", None):
                resposta.append(chunk.text)

        return "".join(resposta).strip()

    # Prompt específico para gerar múltipla escolha
    texto = f"""
CONTEXTO DA TRAGÉDIA: {desastre}
RESPOSTA ANTERIOR DO USUÁRIO: "{question}"
DIRETRIZ DO JOGO: {diretriz}

INSTRUÇÕES PARA GERAR PERGUNTAS:
- Crie 3 perguntas de múltipla escolha baseadas na resposta do usuário
- Cada pergunta deve ter 4 alternativas (A, B, C, D)
- As alternativas devem direcionar para ações práticas e realistas
- Inclua uma opção "fácil" que seja a mais óbvia ou imediata
- Foque em consequências, trade-offs e tomadas de decisão
- Cada pergunta deve ser UMA FRASE apenas
- Formate como JSON

FORMATO DE SAÍDA ESPERADO (JSON):
{{
  "perguntas": [
    {{
      "pergunta": "Texto da pergunta?",
      "alternativas": {{
        "A": "Alternativa A",
        "B": "Alternativa B", 
        "C": "Alternativa C",
        "D": "Alternativa D"
      }},
      "dica_contexto": "Breve explicação do contexto da pergunta"
    }}
  ]
}}

EXEMPLO:
{{
  "perguntas": [
    {{
      "pergunta": "Como priorizar os recursos limitados?",
      "alternativas": {{
        "A": "Focar na população mais afetada",
        "B": "Distribuir igualmente entre todas as áreas",
        "C": "Investir em prevenção futura",
        "D": "Aguardar mais recursos externos"
      }},
      "dica_contexto": "Recursos insuficientes para todas as necessidades"
    }}
  ]
}}
"""

    try:
        resposta_raw = gerar_resposta(texto)

        # Tenta parsear o JSON da resposta
        import json
        resposta_json = json.loads(resposta_raw)

        # Valida estrutura básica
        if "perguntas" not in resposta_json or not isinstance(resposta_json["perguntas"], list):
            raise ValueError("Estrutura de resposta inválida")

        # Salva no banco de dados
        write_bd_5_minutos(task_id, json.dumps(resposta_json))

        print(f"fila: {task_id} \nPerguntas geradas: {len(resposta_json['perguntas'])}")
        return resposta_json

    except json.JSONDecodeError as e:
        # Fallback: se não conseguir parsear JSON, retorna estrutura básica
        fallback = {
            "perguntas": [
                {
                    "pergunta": "Qual ação imediata você priorizaria?",
                    "alternativas": {
                        "A": "Conter a fonte do problema",
                        "B": "Proteger a população afetada",
                        "C": "Mobilizar recursos externos",
                        "D": "Documentar para responsabilização"
                    },
                    "dica_contexto": "Necessidade de ação rápida com recursos limitados"
                }
            ]
        }
        write_bd_5_minutos(task_id, json.dumps(fallback))
        return fallback


def avaliar_progresso_jogo(payload: dict):
    """
    Avalia o progresso da história ambiental e retorna percentual de conclusão
    Determina se o jogo foi concluído com base no cumprimento das normas ambientais
    """
    message = payload
    print("=== AGENTE DE AVALIAÇÃO DE PROGRESSO ===")
    print(message)

    # Extração dos dados do payload
    agent_name = message.get("agent_name", "")
    prompt = message.get("payload", {})
    contexto_historico = message.get("question", "História não fornecida")

    # Dados específicos para avaliação
    contexto_atual = prompt.get("contexto_atual", "")
    desfecho_esperado = prompt.get("desfecho_esperado", "")
    normas_requeridas = prompt.get("normas_ambientais", [])
    acoes_realizadas = prompt.get("acoes_realizadas", [])

    task_id = message.get("task.id", "")
    metadata = message.get("metadata", {})
    user_id = metadata.get("user_id", "")
    trace_id = metadata.get("trace_id", "")

    # Validação básica
    if not contexto_atual:
        return {
            "percentual_conclusao": 0,
            "jogo_concluido": False,
            "mensagem": "Contexto atual não fornecido",
            "detalhes": {}
        }

    def carregar_variaveis_ambiente() -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dotenv_path = os.path.join(base_dir, ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY não encontrada")

    def criar_cliente_genai() -> genai.Client:
        carregar_variaveis_ambiente()
        api_key = os.environ.get("GEMINI_API_KEY")
        return genai.Client(api_key=api_key)

    def gerar_resposta(texto: str, modelo: str = "gemini-flash-lite-latest") -> str:
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("Texto deve ser string não vazia")

        client = criar_cliente_genai()
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=texto)])]

        generate_content_config = types.GenerateContentConfig(
            thinkingConfig={"thinkingBudget": 0},
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )

        resposta = []
        for chunk in client.models.generate_content_stream(
                model=modelo,
                contents=contents,
                config=generate_content_config,
        ):
            if getattr(chunk, "text", None):
                resposta.append(chunk.text)

        return "".join(resposta).strip()

    # Prompt específico para avaliação de progresso
    texto_avaliacao = f"""
CONTEXTO INICIAL DA TRAGÉDIA: {contexto_historico}
ESTADO ATUAL DA SITUAÇÃO: {contexto_atual}
DESFECHO ESPERADO IDEAL: {desfecho_esperado}
NORMAS AMBIENTAIS REQUERIDAS: {normas_requeridas}
AÇÕES JÁ REALIZADAS PELO USUÁRIO: {acoes_realizadas}

ANÁLISE REQUERIDA:
1. Avalie o progresso em relação à resolução completa da tragédia ambiental
2. Considere o cumprimento das normas ambientais brasileiras
3. Verifique se o problema central foi resolvido
4. Atribua uma porcentagem de 0-100% baseada em:
   - Contenção do problema ambiental
   - Recuperação dos ecossistemas afetados
   - Conformidade com leis ambientais
   - Sustentabilidade da solução

CRITÉRIOS PARA 100% DE CONCLUSÃO:
- Todas as normas ambientais foram cumpridas
- O problema central está completamente resolvido
- Não há riscos ambientais remanescentes
- As soluções são sustentáveis a longo prazo

FORMATO DE RESPOSTA (STRICT JSON):
{{
  "percentual_conclusao": 75,
  "jogo_concluido": false,
  "pontos_fortes": [
    "Lista de aspectos bem resolvidos",
    "Máximo 3 itens"
  ],
  "pontos_fracos": [
    "Lista de aspectos pendentes",
    "Máximo 3 itens"
  ],
  "proximos_passos_sugeridos": [
    "Ações para alcançar 100%",
    "Máximo 3 itens"
  ],
  "mensagem_parabens": "Mensagem motivacional se acima de 80%",
  "analise_detalhada": "Breve explicação do percentual atribuído"
}}

IMPORTANTE: 
- Seja rigoroso na avaliação
- 100% só se TODOS os critérios forem atendidos
- Considere a realidade das normas ambientais brasileiras
"""

    try:
        resposta_raw = gerar_resposta(texto_avaliacao)

        # Parse da resposta
        import json
        avaliacao = json.loads(resposta_raw)

        # Validação da estrutura
        required_fields = ["percentual_conclusao", "jogo_concluido", "pontos_fortes", "pontos_fracos"]
        for field in required_fields:
            if field not in avaliacao:
                raise ValueError(f"Campo obrigatório '{field}' não encontrado")

        # Ajusta jogo_concluido baseado no percentual
        if avaliacao["percentual_conclusao"] >= 100:
            avaliacao["jogo_concluido"] = True
            avaliacao[
                "mensagem_parabens"] = "🎉 PARABÉNS! Você resolveu completamente a tragédia ambiental, cumprindo todas as normas e criando uma solução sustentável!"

        # Salva no banco de dados
        write_bd_5_minutos(task_id, json.dumps(avaliacao))

        print(f"✅ Avaliação concluída - Progresso: {avaliacao['percentual_conclusao']}%")
        return avaliacao

    except json.JSONDecodeError as e:
        print(f"❌ Erro no JSON: {e}")
        # Fallback em caso de erro
        fallback = {
            "percentual_conclusao": 0,
            "jogo_concluido": False,
            "pontos_fortes": ["Sistema de avaliação ativo"],
            "pontos_fracos": ["Não foi possível analisar o progresso"],
            "proximos_passos_sugeridos": ["Revisar as ações realizadas"],
            "analise_detalhada": "Erro na análise do progresso"
        }
        write_bd_5_minutos(task_id, json.dumps(fallback))
        return fallback


def atualizar_contexto_historico(payload: dict):
    """
    Atualiza e resume o contexto histórico baseado na última pergunta e resposta
    Retorna um novo contexto condensado para substituir o anterior
    """
    message = payload
    print("=== AGENTE DE ATUALIZAÇÃO DE CONTEXTO ===")
    print(message)

    # Extração dos dados do payload
    agent_name = message.get("agent_name", "")
    prompt = message.get("payload", {})

    # Dados para atualização do contexto
    contexto_atual = prompt.get("contexto_atual", "")
    ultima_pergunta = prompt.get("ultima_pergunta", "")
    resposta_usuario = prompt.get("resposta_usuario", "")
    acoes_anteriores = prompt.get("acoes_anteriores", [])

    task_id = message.get("task.id", "")
    metadata = message.get("metadata", {})
    user_id = metadata.get("user_id", "")
    trace_id = metadata.get("trace_id", "")

    # Validação básica
    if not contexto_atual or not resposta_usuario:
        return {
            "novo_contexto": contexto_atual or "Contexto não disponível",
            "resumo_mudancas": "Nenhuma atualização possível - dados insuficientes",
            "contexto_atualizado": False
        }

    def carregar_variaveis_ambiente() -> None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dotenv_path = os.path.join(base_dir, ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY não encontrada")

    def criar_cliente_genai() -> genai.Client:
        carregar_variaveis_ambiente()
        api_key = os.environ.get("GEMINI_API_KEY")
        return genai.Client(api_key=api_key)

    def gerar_resposta(texto: str, modelo: str = "gemini-flash-lite-latest") -> str:
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("Texto deve ser string não vazia")

        client = criar_cliente_genai()
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=texto)])]

        generate_content_config = types.GenerateContentConfig(
            thinkingConfig={"thinkingBudget": 0},
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ],
        )

        resposta = []
        for chunk in client.models.generate_content_stream(
                model=modelo,
                contents=contents,
                config=generate_content_config,
        ):
            if getattr(chunk, "text", None):
                resposta.append(chunk.text)

        return "".join(resposta).strip()

    # Prompt específico para resumo e atualização de contexto
    texto_atualizacao = f"""
CONTEXTO ATUAL DA HISTÓRIA:
{contexto_atual}

ÚLTIMA INTERAÇÃO:
- Pergunta feita: {ultima_pergunta}
- Resposta do usuário: {resposta_usuario}

AÇÕES ANTERIORES REGISTRADAS:
{acoes_anteriores}

INSTRUÇÕES PARA ATUALIZAÇÃO:
1. INCORPORE a resposta do usuário ao contexto existente
2. MANTENHA apenas informações RELEVANTES para o progresso da história
3. CONDENSE o texto para ser mais conciso (máximo 300 palavras)
4. DESTAQUE mudanças significativas no cenário ambiental
5. PRESERVE a continuidade narrativa
6. REGISTRE consequências das ações tomadas

FORMATO DE SAÍDA (STRICT JSON):
{{
  "novo_contexto": "Texto condensado e atualizado incorporando a última resposta",
  "resumo_mudancas": "Breve descrição do que mudou com esta interação",
  "acoes_realizadas": [
    "Lista atualizada de ações importantes realizadas",
    "Inclua a nova ação baseada na resposta do usuário"
  ],
  "alertas_importantes": [
    "Problemas emergentes ou consequências inesperadas",
    "Máximo 2 itens se aplicável"
  ],
  "contexto_atualizado": true
}}

EXEMPLO:
{{
  "novo_contexto": "Após o vazamento químico no rio, o usuário optou por isolar a área com barreiras. Isso contém a contaminação, mas comunidades a jusante começam a relatar escassez de água. A qualidade do ar na região piorou devido à evaporação dos químicos.",
  "resumo_mudancas": "Área isolada contendo contaminação, mas surgem problemas de acesso à água e qualidade do ar",
  "acoes_realizadas": ["Isolamento da área contaminada"],
  "alertas_importantes": ["Escassez de água em comunidades a jusante", "Qualidade do ar comprometida"],
  "contexto_atualizado": true
}}

DIRETRIZES IMPORTANTES:
- Seja objetivo e factual
- Não invente informações não presentes no contexto
- Destaque tanto progressos quanto problemas emergentes
- Mantenha o foco na tragédia ambiental e suas consequências
"""

    try:
        resposta_raw = gerar_resposta(texto_atualizacao)

        # Parse da resposta
        import json
        contexto_atualizado = json.loads(resposta_raw)

        # Validação da estrutura
        required_fields = ["novo_contexto", "resumo_mudancas", "acoes_realizadas", "contexto_atualizado"]
        for field in required_fields:
            if field not in contexto_atualizado:
                raise ValueError(f"Campo obrigatório '{field}' não encontrado")

        # Garante que ações_realizadas seja uma lista
        if not isinstance(contexto_atualizado["acoes_realizadas"], list):
            contexto_atualizado["acoes_realizadas"] = [contexto_atualizado["acoes_realizadas"]]

        # Salva no banco de dados
        write_bd_5_minutos(task_id, json.dumps(contexto_atualizado))

        print(f"✅ Contexto atualizado - Mudanças: {contexto_atualizado['resumo_mudancas']}")
        return contexto_atualizado

    except json.JSONDecodeError as e:
        print(f"❌ Erro no JSON: {e}")
        # Fallback: mantém contexto anterior com marcação de falha
        fallback = {
            "novo_contexto": contexto_atual,
            "resumo_mudancas": "Falha na atualização - contexto mantido sem alterações",
            "acoes_realizadas": acoes_anteriores or [],
            "alertas_importantes": ["Sistema de atualização temporariamente indisponível"],
            "contexto_atualizado": False
        }
        write_bd_5_minutos(task_id, json.dumps(fallback))
        return fallback