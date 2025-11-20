# Estágio 1: Imagem base com Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /sisagent2_app

# Copia o arquivo de dependências da raiz do projeto para o contêiner
# Isso permite que o sisMQ tenha suas próprias dependências no futuro, se necessário
COPY ../requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos da pasta sisMQ (local) para o diretório de trabalho no contêiner
COPY . .

# Comando que será executado quando o contêiner iniciar
CMD ["python", "main.py"]
