FROM python:3.10-slim

# 1. Dossier de travail
WORKDIR /app

# 2. On copie d'abord le requirements pour profiter du cache Docker
COPY requirements.txt .

# 3. Installation des librairies
RUN pip install --no-cache-dir -r requirements.txt

# 4. On copie le reste du code
COPY . .

# 5. Démarrage de l'UI pour Azure (On lance le fichier Dash !)
CMD ["python", "UI.py"]