# Utiliser une image Python officielle
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier tous les fichiers de l'application
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p pages/image data

# Exposer le port Streamlit (par défaut 8501)
EXPOSE 8501

# Vérifier la santé de l'application
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Commande pour lancer l'application
ENTRYPOINT ["streamlit", "run", "pages/app.py", "--server.port=8501", "--server.address=0.0.0.0"]