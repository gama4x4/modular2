# Etapa base com Python
FROM python:3.10-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia tudo para o container
COPY . /app

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando padrão ao rodar o container
CMD ["python", "run_workers.py"]
