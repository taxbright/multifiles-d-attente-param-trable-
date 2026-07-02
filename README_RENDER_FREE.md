# Déploiement Render Free — MultiQueue

## Réglage recommandé dans Render

Créez un **Web Service** avec :

- **Instance Type** : Free
- **Root Directory** : `multiqueue`
- **Build Command** : `./build.sh`
- **Start Command** : `gunicorn multiqueue.wsgi:application`

Le fichier `build.sh` installe les dépendances, exécute `collectstatic` et applique les migrations.

## Variables d’environnement à ajouter

```text
DEBUG=False
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
PYTHON_VERSION=3.14.3
SECRET_KEY=<clé longue et secrète>
```

## Base de données en mode gratuit

Le projet peut démarrer avec SQLite, mais ce n’est pas recommandé sur Render Free : le système de fichiers est éphémère, donc les données SQLite peuvent disparaître après redéploiement, redémarrage ou mise en veille.

Pour garder les données gratuitement plus longtemps, utilisez une base PostgreSQL externe gratuite comme Supabase, puis ajoutez :

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
USE_SUPABASE=True
DATABASE_SSLMODE=require
DATABASE_CONN_MAX_AGE=0
```

## Après déploiement

1. Ouvrez `https://votre-service.onrender.com/register/`.
2. Créez le premier compte administrateur.
3. Connectez-vous et vérifiez la page d’accueil.
4. Ouvrez un département, puis `Gérer les guichets`.
5. Cliquez sur **Tester la voix**, puis sur le bouton téléphone d’un guichet pour appeler un ticket.

## Notes Render Free

- Le service peut se mettre en veille après une période d’inactivité.
- Au premier accès après veille, le démarrage peut être lent.
- Les fichiers locaux ne sont pas persistants en Free ; évitez SQLite pour les données importantes.
