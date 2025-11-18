# Painel de Controle e Gateway de Agentes

Este projeto é uma aplicação web robusta construída com Flask, que serve como um painel de controle e um gateway para agentes de IA assíncronos. Ele oferece recursos de segurança, monitoramento de sistema, gerenciamento de filas de tarefas e uma arquitetura escalável para invocar "lambdas" (agentes) em segundo plano.

---

## 🏗️ Arquitetura

O projeto é dividido em duas partes principais:

1.  **Backend**: A API Flask, o painel de controle, os workers Celery e toda a lógica de negócio.
2.  **Frontend**: A interface do usuário (ainda a ser desenvolvida) que consome a API do backend.

---

## Backend (API e Painel de Controle)

<details>
<summary><strong>Clique para expandir as instruções do Backend</strong></summary>

### 🖥️ Interface Web

O projeto inclui um painel de controle administrativo completo, acessível via navegador após o login. Ele oferece as seguintes funcionalidades:

-   **Dashboard**: Gráficos em tempo real sobre o uso de recursos (CPU/Memória), status das requisições, acessos recentes e segurança.
-   **Monitoramento**: Logs detalhados de requisições, lista de IPs bloqueados e contagem de tentativas de login falhas.
-   **Fila**: Visualização ao vivo das tarefas que estão na fila aguardando processamento pelos workers.
-   **Agentes**: Interface para interagir com os agentes (a ser implementada).
-   **Usuários**: Gerenciamento de usuários do painel.

### 🚀 Instalação e Execução

Com o Docker e o Docker Compose instalados, a execução do projeto se resume a dois passos.

1.  **Configure o Ambiente**:
    Crie um arquivo `.env` na raiz do projeto, copiando o conteúdo do `.env.example`, e preencha com suas chaves de API. Para rodar com Docker, a variável `REDIS_HOST` deve ser `redis`.
    ```
    # .env
    SECRET_KEY="sua-chave-secreta-super-segura"
    GEMINI_API_KEY="sua-chave-da-api-do-gemini"
    REDIS_PORT=16379
    REDIS_HOST=redis
    DEFAULT_ADMIN_USER=admin
    DEFAULT_ADMIN_PASSWORD=changeme
    AGENT_API_COOLDOWN_SECONDS=15
    ```

2.  **Inicie a Aplicação**:
    Execute o seguinte comando na raiz do projeto. Ele irá construir as imagens, iniciar os contêineres da aplicação, do worker e do Redis, e preparar o banco de dados.
    ```bash
    docker-compose up --build
    ```

3.  **Acesse o Painel**:
    Após a inicialização, abra seu navegador e acesse `http://localhost:5000`.

Para parar todos os serviços, pressione `Ctrl+C` no terminal onde o `docker-compose` está rodando, ou execute `docker-compose down` em outro terminal.

### 🤖 Documentação da API de Agentes

Esta API permite a comunicação assíncrona com os agentes de IA.

#### Passo 1: Enviar a Pergunta e Enfileirar a Tarefa

O cliente envia a pergunta, que é colocada em uma fila de processamento. A API retorna imediatamente um ID para rastreamento.

-   **Endpoint**: `POST /api/agents/ask-async`
-   **Corpo da Requisição (JSON)**: `{"question": "Qual a capital do Brasil?"}`
-   **Resposta de Sucesso (`202Accepted`)**:
    ```json
    {
      "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "trace_id": "uuid-para-rastreabilidade-completa",
      "status_url": "http://localhost:5000/api/agents/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
    ```

#### Passo 2: Consultar o Status e Obter a Resposta

O cliente usa o `task_id` para consultar o `status_url` periodicamente (polling) até que a tarefa esteja concluída.

-   **Endpoint**: `GET /api/agents/status/<task_id>`
-   **Respostas Possíveis**:
    -   `{"status": "PENDING"}` (202 Accepted): A tarefa ainda está na fila ou em processamento.
    -   `{"status": "SUCCESS", "answer": "A resposta do agente."}` (200 OK): A tarefa foi concluída.
    -   `{"status": "FAILURE", "error": "Descrição do erro."}` (500 Internal Server Error): A tarefa falhou.

### 🔑 Documentação da API Principal

APIs para gerenciamento do painel e autenticação.

-   **`POST /api/login`**:
    -   **Descrição**: Autentica um usuário. Aceita dados de formulário ou JSON.
    -   **Corpo**: `{"username": "...", "password": "..."}`
    -   **Resposta**: `{"success": true, "redirect_url": "/dashboard"}` ou `{"error": "Credenciais inválidas."}` (401).

-   **`POST /api/users`**:
    -   **Descrição**: Cria um novo usuário (requer login).
    -   **Corpo (JSON)**: `{"username": "novo_usuario"}`
    -   **Resposta**: `{"success": true, "message": "Usuário ... criado com sucesso."}` ou `{"error": "..."}` (400/409).

-   **`GET /api/system_stats`**:
    -   **Descrição**: Retorna o uso atual de CPU e memória em tempo real (requer login).
    -   **Resposta**: `{"cpu": 25.5, "memory": 60.1}`

### ⚙️ Configuração e Monitoramento

-   **Configuração**: Todas as configurações de ambiente, como chaves de API, porta do Redis e credenciais do administrador padrão, são gerenciadas no arquivo `.env`.
-   **Segurança**: O sistema implementa bloqueio de IP por força bruta contra ataques de login. Os dados de segurança (IPs bloqueados, tentativas falhas) são armazenados de forma persistente no Redis.
-   **Monitoramento**: A interface web oferece visualizações detalhadas sobre a saúde e a segurança do sistema.

</details>

---

## Frontend

A estrutura e as instruções para o frontend serão adicionadas aqui. O frontend será responsável por consumir a API documentada acima para fornecer uma experiência de usuário interativa.
