# Projet Enron Discovery

# Projet Enron Discovery - Plateforme d'investigation e-Discovery

## 📋 Contexte du projet

Ce projet a pour objectif de concevoir un outil d'aide à l'investigation numérique basé sur le **Enron Corpus**, un jeu de données contenant plus de 500 000 emails issus d'une entreprise réelle après un scandale financier majeur.

La mission consiste à transformer une masse de données brutes non structurées en une **application web fonctionnelle** permettant à des journalistes ou des auditeurs de :
- Naviguer dans les échanges
- Identifier des acteurs clés
- Rechercher des informations critiques
- Reconstruire des fils de discussion

---

##  Architecture technique

La stack technique a été choisie pour sa robustesse et sa capacité à passer à l'échelle :

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| Backend | Django 5.2 | Framework web principal |
| Base de données | SQLite (développement) / PostgreSQL (production) | Stockage des données structurées |
| Parsing | Python (email, pandas) | Extraction des emails bruts |
| Frontend | Bootstrap 5 + Chart.js | Interface utilisateur responsive |
| Conteneurisation | Docker | Isolation de PostgreSQL |
| Versionnage | Git | Gestion du code source |

---

## Fonctionnalités implémentées

- ✅ **Dashboard** : Statistiques globales (490 847 emails, 77 780 personnes)
- ✅ **Graphique** : Volume d'emails par mois (1998-2002)
- ✅ **Top 10** : Classement des expéditeurs les plus actifs
- ✅ **Recherche avancée** : Par mots-clés, dates et expéditeur
- ✅ **Autocomplétion** : Suggestions de sujets et d'expéditeurs en temps réel
- ✅ **Explorateur de threads** : Visualisation des conversations chronologiques
- ✅ **Nettoyage des données** : Gestion des encodages et suppression des signatures
- ✅ **Index GIN** : Prêt pour la recherche plein texte avec PostgreSQL

---

## 🗄️ Modélisation des données (MCD)

### Choix de modélisation

La conception du schéma relationnel a fait l'objet d'une attention particulière pour garantir :
- **Normalisation** : Séparation des entités pour éviter la redondance
- **Intégrité référentielle** : Contraintes de clés étrangères
- **Performance** : Index adaptés aux requêtes fréquentes

### Schéma relationnel


![Schéma relationnel](docs/schema.jpg)

#### Relations
- **1 Personne** peut envoyer **plusieurs Emails** (relation 1 → N)
- **1 Email** peut avoir **plusieurs Destinataires** (relation 1 → N)
- **1 Destinataire** lie **1 Email** à **1 Personne** (table de liaison)
- **1 Email** peut répondre à **1 autre Email** (auto-référence via `reponse_a_id`)
#### Fil de discussion
Structure implicite créée par le champ `reponse_a_id` qui permet de reconstruire les conversations.



### Description des entités

#### **Personne**
Stocke tous les acteurs (expéditeurs et destinataires) de manière unique.
- `id` : identifiant unique auto-généré
- `courriel` : adresse email normalisée (contrainte d'unicité)
- `nom` : nom de la personne (peut être vide)

#### **Email**
Représente un message électronique.
- `id` : identifiant unique
- `message_id` : identifiant unique du message (header Message-ID)
- `expediteur_id` : clé étrangère vers l'expéditeur
- `sujet` : objet du message
- `corps` : corps du message (texte brut)
- `date` : date d'envoi
- `reponse_a_id` : auto-référence vers l'email parent (pour les threads)
- `dossier` : retrace l'arborescence des fichiers(inbox, sent, etc.)

#### **Destinataire**
Gère la relation many-to-many entre emails et personnes avec typage.
- `id` : identifiant unique
- `email_id` : clé étrangère vers l'email concerné
- `personne_id` : clé étrangère vers la personne destinataire
- `type` : nature de la relation ('to', 'cc', 'bcc')
- Contrainte d'unicité : (email, personne, type)

### Indexation et optimisation

```sql
-- Index pour recherche chronologique
CREATE INDEX idx_email_date ON email(date);

-- Index pour recherche par expéditeur
CREATE INDEX idx_email_expediteur ON email(expediteur_id);

-- Index GIN pour recherche plein texte (PostgreSQL)
CREATE INDEX idx_email_corps_gin ON email USING GIN(to_tsvector('french', corps));

-- Index composites pour Destinataire
CREATE INDEX idx_destinataire_email_personne ON destinataire(email_id, personne_id);

##Justification des choix :
-Table Personne séparée : Évite la redondance des adresses email et permet de suivre l'activité d'un acteur sur plusieurs messages
-Table Destinataire : Modélise correctement la cardinalité (un email → plusieurs destinataires) avec conservation du type (to/cc)
-Champ reponse_a_id : Permet la reconstruction des fils de discussion sans table dédiée

Index GIN : Optimise les recherches textuelles sur 500 000+ messages

## Extraction et parsing
Le script `scripts/import_enron.py` assure l ingestion 'des données' :
# Extraits significatifs du parsing

def parse_email_file(file_path, folder_name):
    """Parse un fichier .eml et extrait les métadonnées"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        msg = email.message_from_file(f)
    
    # Extraction des headers
    message_id = msg.get('Message-ID', '').strip('<>')
    from_addr = clean_email(msg.get('From', ''))
    to_addrs = parse_addresses(msg.get('To', ''))
    # ...

# Étapes du pipeline :

-Parcours  de l'arborescence maildir/(racine)
-Extraction des métadonnées avec la librairie standard email
-Nettoyage et normalisation des adresses
-Extraction du corps du message
-Nettoyage des signatures (suppression des pieds de page)
-Insertion en base avec gestion des clés étrangères

# Gestion des particularités du dataset

-Absence de pièces jointes : Le dataset officiel n en contient pas, table Attachment supprimée
-Adresses normalisées : Les emails invalides sont convertis en utilisateur@enron.com
-Encodages variés : Gestion des erreurs avec errors='ignore'

## Interface Web
# Dashboard 'global'

-Le dashboard présente des statistiques descriptives avec Chart.js :
-Volume de mails par mois : Graphique linéaire interactif avec filtres de période
-Top 10 des expéditeurs : Tableau des acteurs les plus actifs
-Métriques globales : Total emails, personnes uniques, période couverte

# Vue dashboard (extrait)
def dashboard(request):
    total_emails = Email.objects.count()
    total_persons = Person.objects.count()
    monthly_counts = Email.objects.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(count=Count('id'))
    # ...

# Moteur de recherche

Recherche avancée avec :
-Autocomplétion : Suggestions de sujets et d expéditeurs en temps réel
-Mots-clés sur le sujet et le corps des messages (icontains)
-Filtrage par plage de dates
-Filtrage par expéditeur
def suggest_email_subjects(request):
    """API d'autocomplétion pour sujets et expéditeurs"""
    # ...

# Explorateur de threads
Affichage chronologique d un email et de toutes ses réponses :
-L email original est mis en évidence (cadre bleu)
-Les réponses sont affichées dans l ordre
-Liens vers les messages parents
-Affichage des destinataires

# Déploiement avec Docker
Le fichier `docker-compose.yml` permet de lancer PostgreSQL de manière isolée :
version: '3.8'
services:
  postgres:
    image: postgres:15
    container_name: enron_postgres
    environment:
      POSTGRES_DB: enron_db
      POSTGRES_USER: enron_user
      POSTGRES_PASSWORD: enron_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

## Passage de SQLite à PostgreSQL
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'enron_db',
        'USER': 'enron_user',
        'PASSWORD': 'enron_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

## Migration des données
# Sauvegarde des données SQLite
python manage.py dumpdata > data_backup.json

# Bascule vers PostgreSQL
docker-compose up -d
python manage.py migrate
python manage.py loaddata data_backup.json

# Installation et exécution

# Prérequis
-Python 3.11+
-Docker (optionnel, pour PostgreSQL)
-Git

## Étapes d installation :

# 1. Cloner le dépôt
git clone https://github.com/yvesgnonhoue/enron-discovery.git
cd enron-discovery

# 2. Créer l environnement virtuel
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la base de données
python manage.py migrate

# 5. Lancer le serveur
python manage.py runserver

## Import des données :
# Placer les emails extraits dans data/maildir/
cd scripts
python import_enron.py


## Statistiques sur le dataset
-Nombre total d emails : 490 847
-Nombre de personnes uniques : 77 780
-Période couverte : 1998-2002 (après filtrage des dates aberrantes)
-Taille des données : 1.7 Go (compressé)
-Affichage d un email et de toutes les réponses associées sous forme de conversation chronologique.

👥 Auteurs
AWANDE Carmel - Développement & Modélisation
GNONHOUE Yves - Développement & Tests
Projet réalisé dans le cadre du cours de Structure des données.

📝 Notes importantes
-Les données brutes (dossier data/) ne sont pas incluses dans le dépôt Git
-L application utilise SQLite par défaut pour le développement
-Le passage à PostgreSQL est documenté et prêt via Docker
-Les index GIN sont actifs uniquement avec PostgreSQL

🔗 Lien du dépôt
https://github.com/yvesgnonhoue/enron-discovery





