# Projeto API Gateway com Flask

Este projeto é um gateway de API seguro construído com Flask. Ele foi projetado para servir como uma camada intermediária entre clientes e serviços, oferecendo recursos de segurança, monitoramento e a capacidade de servir tanto conteúdo dinâmico (via API) quanto estático (HTML/CSS/JS).

---

<details>
<summary><strong>🚀 Instalação e Execução</strong></summary>

### Opção 1: Usando Docker (Recomendado)
Esta é a maneira mais simples de executar o projeto, pois gerencia todas as dependências em um contêiner isolado.

**Pré-requisitos:**
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

**Comando:**
Execute o seguinte comando na raiz do projeto:
```bash
docker-compose up --build
```
A aplicação estará disponível em `http://localhost:5000`.

### Opção 2: Ambiente Local (Python)

**a. Crie e Ative um Ambiente Virtual:**
```bash
# Cria o ambiente
python -m venv .venv

# Ativa o ambiente (macOS/Linux)
source .venv/bin/activate
# Ou (Windows)
# .venv\Scripts\activate
```

**b. Instale as Dependências:**
```bash
pip install -r requirements.txt
```

**c. Execute a Aplicação:**
```bash
python app.py
```
A aplicação estará rodando em `http://localhost:5000`.

</details>

---

<details>
<summary><strong>💻 Como Usar a Aplicação</strong></summary>

### Acessando o Painel de Monitoramento (via Navegador)
O painel de monitoramento é uma área protegida para administradores.

1.  **Acesse a Página de Login**:
    Abra seu navegador e vá para `http://localhost:5000/login`.

2.  **Faça o Login**:
    Use as credenciais padrão para entrar:
    - **Usuário**: `admin`
    - **Senha**: `password123`

3.  **Acesse o Painel**:
    Após o login, você será redirecionado para `http://localhost:5000/monitoring`. Nesta página, você pode:
    - Ver IPs atualmente bloqueados.
    - Desbloquear um IP manualmente.
    - Acompanhar o log das últimas 50 requisições.

### Consumindo a API (para Desenvolvedores)
O gateway expõe rotas de API que podem ser consumidas por outras aplicações.

**Endpoint de Login:** `POST /api/login`
- **Descrição**: Autentica um usuário.
- **Exemplo (`curl`):**
  ```bash
  curl -X POST -d "username=admin&password=password123" http://localhost:5000/api/login
  ```
- **Resposta de Sucesso:**
  ```json
  {
    "success": true,
    "message": "Login bem-sucedido!"
  }
  ```
- **Resposta de Falha (Credenciais Inválidas):**
  ```json
  {
    "success": false,
    "error": "Credenciais inválidas."
  }
  ```
- **Resposta de Bloqueio (Status 429):**
  ```json
  {
    "error": "IP bloqueado. Tente novamente em 3590s."
  }
  ```

**Endpoint de Dados Protegidos:** `GET /api/data`
- **Descrição**: Rota de exemplo que retorna dados se o cliente estiver autenticado (a lógica de autenticação para esta rota específica precisa ser implementada, por enquanto ela é pública).
- **Exemplo (`curl`):**
  ```bash
  curl http://localhost:5000/api/data
  ```

### Acessando o Site Estático
O projeto também serve um site estático simples.
- **URL**: `http://localhost:5000/site/html/index.html`

</details>

---

<details>
<summary><strong>⚙️ Configuração e Segurança</strong></summary>

### Ativando/Desativando a Segurança
Você pode ligar ou desligar todos os recursos de segurança (bloqueio de IP, etc.).

- **Arquivo**: `app.py`
- **Variável**: `app.config['SECURITY_ENABLED']`
- **Valores**:
  - `True`: Segurança ativada (padrão).
  - `False`: Segurança desativada.

### Banco de Dados
- O projeto usa **SQLite 3** e armazena todos os dados no arquivo `app.db`.
- A tabela `user` é criada automaticamente na primeira execução.
- **AVISO**: As senhas são atualmente armazenadas em texto plano. Para um ambiente de produção, é **fortemente recomendado** implementar o hashing de senhas (o código contém comentários sobre como fazer isso com `werkzeug.security`).

</details>
