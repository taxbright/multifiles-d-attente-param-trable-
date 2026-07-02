# Configuration Supabase pour Multi-Queue

Cette version peut utiliser Supabase comme base de données PostgreSQL distante.
Django reste le cœur de l'application : modèles, vues, authentification, export CSV et administration.

## 1. Créer la base Supabase

1. Créez un projet sur Supabase.
2. Ouvrez **Project Settings > Database > Connection string**.
3. Copiez la chaîne de connexion PostgreSQL.
4. Remplacez `[YOUR-PASSWORD]` par le mot de passe réel de la base.

Pour un test local, la connexion directe sur le port `5432` convient souvent.
Pour un hébergement serveur/serverless, utilisez plutôt le pooler Supavisor, souvent sur le port `6543`.

## 2. Installer les dépendances

```powershell
pip install -r requirements.txt
```

Le fichier `requirements.txt` contient :

```text
Django>=6.0,<6.1
psycopg[binary]>=3.2
```

## 3. Activer Supabase dans PowerShell

Exemple avec une URL complète :

```powershell
$env:USE_SUPABASE="True"
$env:DATABASE_URL="postgresql://postgres:VOTRE_MOT_DE_PASSE@db.VOTRE_PROJECT_REF.supabase.co:5432/postgres"
$env:DATABASE_SSLMODE="require"
$env:DATABASE_CONN_MAX_AGE="0"
```

Si vous utilisez le pooler Supavisor, l'URL ressemble souvent à ceci :

```powershell
$env:DATABASE_URL="postgresql://postgres.VOTRE_PROJECT_REF:VOTRE_MOT_DE_PASSE@aws-0-REGION.pooler.supabase.com:6543/postgres"
```

## 4. Migrer les tables Django vers Supabase

```powershell
python manage.py migrate
```

Cette commande créera dans Supabase les tables nécessaires : utilisateurs Django, sessions, files, agents et tickets.

## 5. Créer le compte super-utilisateur

```powershell
python manage.py createsuperuser
```

Seul ce type de compte peut accéder à l'application, aux exports, aux données et à l'administration.

## 6. Lancer le serveur

```powershell
python manage.py runserver
```

Puis ouvrir :

```text
http://127.0.0.1:8000/
```

## Sécurité importante

- Ne mettez jamais le mot de passe Supabase dans GitHub.
- Ne partagez pas `DATABASE_URL`.
- Le contrôle “super-utilisateur uniquement” est appliqué côté Django.
- L'accès au tableau de bord Supabase lui-même se règle dans Supabase, avec les membres du projet Supabase.
