# Regras Gerais para a IA neste Projeto - Estilo Carioca

Aê, meu chapa! Presta atenção aqui. Este arquivo é o mapa da mina pra mexer nesse projeto. Segue na disciplina pra gente não ter caô e o código ficar maneiro.

## 1. Visão Geral da Arquitetura

O projeto agora tem dois focos principais:

1.  **Painel de Administração**: A área logada (`/login`, `/monitoring`, etc.) para gerenciar a aplicação, usuários e segurança.
2.  **Motor do RPG Ambiental**: O coração do projeto. É um sistema assíncrono com Front-end (`index.html`), Backend (Flask), Fila (RabbitMQ) e Workers (`sisMQ`) que executam os agentes Gemini.

---

<details>
<summary><strong>🤖 Arquitetura do RPG Ambiental (LEIA COM ATENÇÃO!)</strong></summary>

### Visão Geral do Fluxo do Jogo

1.  **Usuário** abre o `index.html` e inicia um cenário de desastre ambiental.
2.  **Front-end** chama uma rota no backend (`/api/rpg/iniciar`) para começar a história.
3.  **Backend (Flask)** recebe o pedido, monta uma "mensagem-tarefa" e a coloca na fila do **RabbitMQ**.
4.  **Worker (`sisMQ`)**, que tá sempre de olho na fila, pega a tarefa.
5.  O Worker usa um **dispatcher** para chamar a função de agente correta (ex: `processar_mensagem`).
6.  O **Agente (Gemini)** processa a lógica, gera a narrativa ou as perguntas.
7.  O Worker salva o resultado no banco de dados de registros (`registros.db`).
8.  O **Front-end** fica perguntando pro backend (usando um `task_id`) se a tarefa já terminou. Quando termina, ele pega o resultado e mostra a continuação da história pro jogador.

### Contrato de Comunicação (A Regra do Jogo)

#### 1. Front-end ↔ Backend (API REST)

-   **`POST /api/rpg/iniciar`**: Começa um novo jogo.
    -   **Envia**: `{ "user_id": "...", "desastre_inicial": "...", "diretriz_do_jogo": "..." }`
    -   **Recebe**: `{ "trace_id": "...", "task_id": "...", "status": "PENDING" }`

-   **`POST /api/rpg/interagir`**: Envia a resposta do jogador.
    -   **Envia**: `{ "trace_id": "...", "resposta_usuario": "...", "contexto_atual": "..." }`
    -   **Recebe**: `{ "trace_id": "...", "task_ids": {"principal": "..."}, "status": "PENDING" }`

-   **`GET /api/rpg/resultado/<task_id>`**: O front usa essa rota pra saber se a tarefa terminou.
    -   **Recebe**: `{ "status": "READY", "dados": { ...resultado do agente... } }`

#### 2. Backend ↔ Fila (RabbitMQ) ↔ Worker (sisMQ)

O **Backend** (Flask) é o **Produtor**. Ele só monta a mensagem e joga na fila.
O **Worker** (`sisMQ`) é o **Consumidor**. Ele pega a mensagem e faz o trabalho.

-   **Formato da Mensagem na Fila:** O worker espera receber um JSON com essa cara:
    ```json
    {
      "action": "nome_da_funcao_a_chamar",
      "payload": {
        "agent_name": "nome_do_agente_gemini",
        "question": "contexto_geral_da_historia",
        "payload": { ...dados específicos... },
        "metadata": {
          "user_id": "...",
          "trace_id": "...",
          "task.id": "..."
        }
      }
    }
    ```

-   **`ACTION_DISPATCHER` no `sisMQ/main.py`**: É o "case" que direciona o trabalho. Ele mapeia a `action` da mensagem para a função Python correta.
    -   `"processar_mensagem"` → chama o agente que cria a narrativa.
    -   `"gerar_perguntas_multipla_escolha"` → chama o agente que cria as opções.
    -   `"avaliar_progresso_jogo"` → chama o agente que calcula o progresso.
    -   `"atualizar_contexto_historico"` → chama o agente que resume a história.

</details>

---

<details>
<summary><strong>Estilo de Código e Organização</strong></summary>

-   **Organização é tudo!** Agrupa as coisas que trabalham juntas. Funções auxiliares ficam perto da rota que as usa.
-   **Divisórias para Organizar**: Use `#---...` pra separar blocos lógicos.
-   **Funções Complexas em Arquivo Separado**: Lógica pesada vai pra um arquivo separado e a gente importa.
-   **Estrutura do `app.py`**: Imports, configurações, funções auxiliares, e por último, as rotas.

</details>

---

<details>
<summary><strong>Segurança (NÃO DÁ MOLE!)</strong></summary>

-   **SQL Injection**: **NUNCA** use f-strings ou `+` pra montar consulta SQL. Usa sempre `?` (consultas parametrizadas).
-   **Senhas**: Usa `generate_password_hash` e `check_password_hash`. Senha em texto puro é caô.
-   **Mecanismo de Bloqueio**: Entende como o bloqueio de IP funciona antes de mexer em autenticação.

</details>

---

<details>
<summary><strong>Banco de Dados e Vocabulário</strong></summary>

-   **Banco de Dados**: A gente usa `sqlite3` direto na veia. Sem ORM.
-   **Idioma e Sotaque**: O papo é **Português (Brasil)**, com **sotaque carioca** nos comentários. Manda a real, sem formalidade. Usa gírias como "maneiro", "bolado", "caô", "na moral", "parada", "sinistro".

</details>

Seguindo essas regras, o projeto vai ficar show de bola! É nós!
