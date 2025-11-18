# Use uma imagem base oficial do Python
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Impede que o Python gere arquivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1
# Garante que a saída do Python seja exibida imediatamente no terminal do contêiner
ENV PYTHONUNBUFFERED 1

# Copia o arquivo de dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação para o diretório de trabalho
COPY . .

# A porta que a aplicação Flask irá expor
EXPOSE 5000