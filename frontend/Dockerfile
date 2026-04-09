FROM python:3.10-slim

# 1. Dossier de travail
WORKDIR /app

# 2. On copie d'abord le requirements pour profiter du cache Docker
COPY requirements.txt .

# 3. Installation des librairies ET de Gunicorn pour la production
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 4. On copie le reste du code
COPY . .

# 5. On expose le port 8050 (port standard pour Dash)
EXPOSE 8050

# 6. Démarrage avec Gunicorn
# "UI:server" veut dire : Dans le fichier UI.py, utilise la variable 'server'
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "UI:server"]
