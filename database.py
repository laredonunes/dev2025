import sqlite3
import os
from flask import g
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')

def get_db():
    """Abre uma nova conexão com o banco de dados se não houver uma no contexto da requisição."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception=None):
    """Fecha a conexão com o banco de dados."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Cria as tabelas do banco de dados a partir do schema."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            password_reset_required BOOLEAN DEFAULT TRUE
        )
    """)
    db.commit()

def migrate_db():
    """Aplica migrações simples, como adicionar colunas faltantes."""
    db = get_db()
    cursor = db.execute("PRAGMA table_info(user)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'password_reset_required' not in columns:
        db.execute("ALTER TABLE user ADD COLUMN password_reset_required BOOLEAN DEFAULT TRUE")
        db.commit()

def get_user_by_username(username: str):
    """Busca um usuário pelo nome de usuário."""
    return get_db().execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()

def get_all_users():
    """Retorna todos os usuários (ID e username)."""
    return get_db().execute("SELECT id, username FROM user").fetchall()

def delete_user_by_id(user_id: int):
    """Deleta um usuário pelo ID."""
    db = get_db()
    db.execute("DELETE FROM user WHERE id = ?", (user_id,))
    db.commit()

def init_app(app):
    """Registra as funções de banco de dados com a aplicação Flask."""
    app.teardown_appcontext(close_db)