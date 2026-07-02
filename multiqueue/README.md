MultiQueue — Instructions de démarrage

Pré-requis
- Python 3.10+ (vous utilisez Python 3.14 sur ce poste)
- Node/npm non requis pour le moment (frontend statique inclus)

Installation locale (dev)
1. Créez et activez un environnement virtuel:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# ou cmd
.\.venv\Scripts\activate.bat
```

2. Installez les dépendances:

```bash
pip install -r requirements.txt
```

3. Appliquez les migrations et collectez les fichiers statiques:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

4. Créez un superutilisateur (si nécessaire):

```bash
python manage.py createsuperuser
```

5. Démarrez le serveur de développement:

```bash
python manage.py runserver
```

Accès admin
- URL: http://127.0.0.1:8000/admin/
- Un compte admin de test `admin_test` a été créé localement. Mot de passe: `TestAdmin123!` — changez-le dès la première connexion.

Notes importantes
- Le projet est en `DEBUG=True`. Pour une mise en production: mettez `DEBUG=False`, définissez `ALLOWED_HOSTS`, et servez les fichiers statiques via un serveur web (nginx/IIS).
- `STATIC_ROOT` est configuré pour `staticfiles/`; `collectstatic` copie les actifs dans ce dossier.
- Secrets: ne laissez jamais `SECRET_KEY` dans le dépôt public; utilisez des variables d'environnement ou un fichier `.env` (non commité).

Prochaines étapes recommandées
- Remplacer le logo inline par une image fournie (`static/logo.png` ou `static/logo.svg`).
- Tester l'impression et le QR sur les navigateurs cibles (Chrome, Edge, Firefox).
- Ajouter des tests unitaires pour les vues critiques.

Contact
- Si vous voulez, je peux :
  - remplacer le logo par votre fichier,
  - ajouter un endpoint API pour récupérer les tickets,
  - ajouter un scanner live depuis la caméra (getUserMedia + JS lib).


Améliorations design intégrées
- Ajout de `queueapp/static/queueapp/css/react-icons-lite.css` : couche locale d’icônes inspirée de react-icons, compatible avec les classes déjà présentes dans les templates.
- Remplacement de la dépendance CDN Font Awesome par la feuille locale d’icônes.
- Renforcement de `toastify-lite.css` et `toastify-lite.js` pour obtenir des notifications proches de React-Toastify, sans modifier la logique Django existante.
- Conservation des vues, URLs, modèles et traitements AJAX existants.

Mise à jour professionnelle intégrée
- Refonte du fond avec un style institutionnel moderne : dégradé bleu, grille légère, cartes translucides et tableaux propres.
- Correction de la structure HTML de la page de file d'attente.
- Renforcement de la logique FIFO avec transactions pour éviter les incohérences lors des appels ou créations simultanées.
- Répartition automatique améliorée : un ticket est attribué à chaque agent disponible, sans écraser les tickets précédents.
- Ajout de réponses JSON plus complètes pour le tableau de bord : capacité, taux d'occupation, tickets servis, agents disponibles.
- Interface agent modernisée : statistiques, statuts, actions rapides et notifications professionnelles.
- Page ticket modernisée avec QR code, impression et copie des données QR.

## Mise à jour ajoutée : connexion et exportation des tickets

Cette version ajoute :

- une page de connexion avant l'accès à l'application ;
- une protection des pages principales avec `login_required` ;
- une page d'exportation des tickets ;
- un export CSV global ou filtré par file et par statut ;
- des boutons de déconnexion et d'export dans l'interface.

### Création du compte de connexion

Avant d'ouvrir l'application, créez un utilisateur administrateur si vous n'en avez pas encore :

```powershell
python manage.py createsuperuser
```

Puis lancez le serveur :

```powershell
python manage.py runserver
```

L'application demandera maintenant une connexion à l'adresse :

```text
http://127.0.0.1:8000/login/
```

### Exportation des tickets

Après connexion, ouvrez :

```text
http://127.0.0.1:8000/tickets/exports/
```

Vous pouvez exporter :

- tous les tickets ;
- les tickets d'une seule file ;
- les tickets en attente ;
- les tickets déjà traités.

Le fichier exporté est au format CSV avec séparateur `;`, compatible avec Excel.

## Mise à jour : affectation obligatoire à un agent

Cette version bloque l’appel d’un ticket lorsqu’aucun agent n’est disponible.
Lorsqu’un ticket est appelé, il est automatiquement affecté au premier agent disponible selon l’ordre du numéro de guichet. Le nom de l’agent et le numéro du guichet sont renvoyés dans la réponse, affichés dans l’interface, et ajoutés dans l’export CSV.

Après extraction de cette version, exécuter :

```powershell
python manage.py migrate
python manage.py runserver
```
