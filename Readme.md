🛡️ KYC - Operations Center V4 (Azure Cloud Edition)
Un centre d'opérations anti-fraude complet (Know Your Customer) bâti sur une architecture microservices robuste. Ce projet intègre un flux de transactions en temps réel, un moteur de scoring IA et une infrastructure de données Cloud hybride.

🌟 Présentation du projet
Ce projet reproduit le système nerveux central d'une institution financière moderne. Il permet aux équipes d'investigation (Ops) de surveiller les transactions en direct, d'analyser les profils clients à 360° et d'auditer les décisions de blocage grâce à une interface fluide et un registre sécurisé, le tout propulsé par le Cloud Microsoft Azure.

🏗️ Architecture Technique (Stack)
L'application est découpée en microservices pour garantir des performances optimales et une scalabilité Cloud :

🎨 Frontend (Dashboard) : Plotly Dash & Dash Bootstrap Components (Thème Cyborg). Interface réactive "Full Black" optimisée pour les centres de contrôle.

⚙️ Backend (API & Simulateur) : FastAPI (Python) gérant la logique métier, le scoring IA (XGBoost) et la génération de flux de données continus.

🗄️ Base de données (Azure Cloud) : PostgreSQL Flexible Server hébergé sur Microsoft Azure, garantissant une haute disponibilité, une sécurité de niveau entreprise (SSL/TLS) et une persistance des données dans le Cloud.

🔌 ORM & Connexion : SQLAlchemy avec gestion de pool de connexions (pool_pre_ping) pour une résilience maximale face aux micro-coupures réseau du Cloud.

🐳 Orchestration : Docker & Docker Compose pour un environnement de développement identique à la production.

🚀 Déploiement Cloud (Azure App Services)
Le projet est conçu pour être déployé en tant que services conteneurisés :

API Service : Hébergé sur Azure App Service (Linux).

UI Service : Hébergé sur Azure App Service (Linux).

Database : Instance Azure Database for PostgreSQL.

💻 Guide de Démarrage (Local)
1. Prérequis
Docker Desktop installé et lancé.

Accès réseau au serveur Azure PostgreSQL (ou une instance locale).

2. Installation
Bash
git clone https://github.com/tourki23/kyc-dash-full-azure.git
cd kyc-dash-full-azure
3. Configuration des Variables d'Environnement (.env)
Créez un fichier .env à la racine pour sécuriser vos accès Azure :

Plaintext
DATABASE_URL="postgresql://sqladmin:VOTRE_PASSWORD@kyc-db-server-mahmoud-2026.postgres.database.azure.com:5432/postgres?sslmode=require"
API_URL="http://localhost:8000"
4. Lancement avec Docker Compose
Bash
docker compose up --build -d
5. Migration et Initialisation (Data Seeding)
Pour remplir votre base Azure avec les profils clients initiaux :

Bash
docker compose exec api python Seed_script_migration_data_csv_to_postedreSQL.py
🕹️ Fonctionnalités Clés
🔥 Le Moteur de Simulation Live
Monitoring : Visualisation en temps réel des scores de risque.

Interactivité : Boutons Start/Stop pilotant un sous-processus de simulation de transactions bancaires.

Scoring IA : Chaque transaction est évaluée instantanément par un modèle XGBoost entraîné sur des données de fraude financière.

🔍 Vision Client 360 & Audit
Profiling : Analyse profonde des segments clients (PPE, Suspect, Normal).

Traçabilité : Registre d'audit immuable avec horodatage et hachage unique pour chaque décision prise par l'IA.

👨‍💻 Développé par
Mahmoud TOURKI Expertise : Data Engineering, Cloud Architecture (Azure), Fullstack Python.

💼 LinkedIn

📧 Email