# Regras Gerais para a IA neste Projeto - Estilo Carioca

Aê, meu chapa! Presta atenção aqui. Este arquivo é o mapa da mina pra mexer nesse projeto. Segue na disciplina pra gente não ter caô e o código ficar maneiro.

## 1. Visão Geral da Arquitetura

O projeto é um **Gateway de API seguro**, tipo um porteiro bolado, feito com **Flask**. A parada tem três partes principais:

1.  **API Backend (`/api/*`)**: As rotas que fazem o trabalho sujo, com a lógica de negócio. Tem que ter segurança reforçada.
2.  **Painel de Administração (`/login`, `/monitoring`)**: A área VIP, feita com Jinja2 (da pasta `templates`), pra gerenciar e ficar de olho no movimento.
3.  **Site Estático (`/site/*`)**: A fachada da loja. Páginas HTML/CSS/JS que são servidas na moral, sem passar pela lógica do Flask.

## 2. Meu Estilo de Código (LEIA COM ATENÇÃO!)

Pra gente se entender, o código tem que seguir a minha linha.

-   **Organização é tudo!** Gosto de agrupar as coisas que trabalham juntas. Se tem uma rota de login, as funções auxiliares dela ficam logo acima.

-   **Divisórias para Organizar**: Use comentários com hífens pra separar blocos lógicos. Fica mais fácil de achar as paradas. Exemplo:
    ```python
    #-----------------------------------------------------------------------
    # BLOCO DE AUTENTICAÇÃO: Funções e Rota de Login
    #-----------------------------------------------------------------------

    def funcao_auxiliar_do_login():
        # ...

    @app.route('/login')
    def login():
        # ...
    ```

-   **Funções Complexas em Arquivo Separado**: Se uma função ficar muito sinistra, com muita lógica, a gente joga ela pra um outro arquivo Python (tipo um `utils.py`) e importa. Assim o `app.py` fica mais limpo e é mais fácil de achar erro.

-   **Estrutura do `app.py`**: Primeiro vêm os imports, depois as configurações, aí as funções auxiliarias (agrupadas por função) e, por último, as rotas do Flask.

## 3. Segurança em Primeiro Lugar (NÃO DÁ MOLE!)

Segurança aqui é papo sério.

-   **NUNCA, JAMAIS, EM HIPÓTESE ALGUMA** use f-strings ou concatenação pra montar consulta SQL. É caô na certa! Usa sempre consulta parametrizada (`?`) pra não dar brecha pra SQL Injection.
    -   **Certo (Na moral):** `db.execute("SELECT * FROM user WHERE username = ?", (username,))`
    -   **Errado (Vai dar ruim):** `db.execute(f"SELECT * FROM user WHERE username = '{username}'")`

-   **Senha é Segredo**: A gente não guarda senha dos outros em texto puro. O esquema é usar `werkzeug.security.generate_password_hash` pra guardar e `check_password_hash` pra conferir.

-   **Mecanismo de Bloqueio**: Aquele esquema de bloquear IP (`failed_attempts`, `blocked_ips`) é o segurança da nossa festa. Entende ele antes de mexer em qualquer coisa de login.

## 4. Banco de Dados

-   **É na Raiz**: A gente tá usando `sqlite3` direto na veia. Nada de ORM (SQLAlchemy) por enquanto.
-   **Conexão na Boa**: Usa `get_db()` pra pegar a conexão e deixa que o `@app.teardown_appcontext` fecha ela no final. Sem neurose.

## 5. Estilo de Código e Vocabulário

-   **Idioma**: O papo aqui é **Português (Brasil)**.
-   **Sotaque**: Nos comentários, pode mandar a real, no **estilo carioca**. Sem formalidade, como se estivesse trocando uma ideia com um amigo. Usa gírias como "maneiro", "bolado", "caô", "na moral", "parada", "sinistro".
-   **Clareza**: O código tem que ser fácil de entender. Escreve o papo reto, sem inventar muita moda.

Seguindo essas regras, o projeto vai ficar show de bola! É nós!
