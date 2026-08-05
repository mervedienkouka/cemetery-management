# Guide de déploiement — Render (gratuit, sans carte bancaire)

Ce guide déploie les 3 morceaux du projet : la base PostgreSQL, le backend
Django, et le frontend Flet. Compte à rebours réaliste : **15-20 minutes**.

## 0. Prérequis

- Un compte GitHub (gratuit) — Render déploie à partir d'un dépôt Git.
- Un compte Render (gratuit, sans carte bancaire) : https://render.com

## 1. Mettre le code sur GitHub

Depuis le dossier `cemetery-management/` (celui qui contient `backend/`,
`frontend/`, `render.yaml`) :

```bash
git init
git add .
git commit -m "Projet cimetière - version finale"
```

Crée un nouveau dépôt vide sur GitHub (bouton "New repository", ne coche
RIEN — pas de README, pas de .gitignore, pas de licence), puis :

```bash
git remote add origin https://github.com/TON-COMPTE/cemetery-management.git
git branch -M main
git push -u origin main
```

Le `.gitignore` fourni exclut déjà `venv/` et `.env` (qui contient ton mot
de passe Gmail) — ils ne partiront pas sur GitHub. C'est voulu.

## 2. Déployer sur Render via le Blueprint

1. Connecte-toi sur https://render.com
2. Clique **New +** → **Blueprint**
3. Connecte ton compte GitHub, sélectionne le dépôt `cemetery-management`
4. Render détecte automatiquement le fichier `render.yaml` à la racine et
   propose de créer 3 ressources : `cemetery-db` (PostgreSQL),
   `cemetery-backend` (Django), `cemetery-frontend` (Flet)
5. Clique **Apply** — Render construit et déploie tout. Ça prend 5-10
   minutes la première fois (installation des dépendances + migrations).

## 3. Relier le frontend au backend (étape manuelle obligatoire)

Le fichier `render.yaml` met une URL de backend par défaut
(`cemetery-backend.onrender.com`), mais si Render choisit un nom légèrement
différent (ex. `cemetery-backend-ab12`), il faut corriger à la main :

1. Une fois `cemetery-backend` déployé, copie son URL réelle (visible en
   haut de sa page Render, du style
   `https://cemetery-backend-xxxx.onrender.com`)
2. Va sur le service `cemetery-frontend` → onglet **Environment**
3. Modifie la variable `API_BASE_URL` pour qu'elle vaille exactement :
   `https://cemetery-backend-xxxx.onrender.com/api` (avec le `/api` à la fin)
4. Sauvegarde — Render redéploie automatiquement le frontend avec la bonne
   URL.

## 4. Activer le vrai envoi d'email (MFA)

Sans ça, le code de vérification MFA ne partira jamais (comportement par
défaut : juste affiché dans les logs du serveur, invisible pour un
utilisateur réel). Sur le service `cemetery-backend` → **Environment**,
ajoute :

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ton_adresse@gmail.com
EMAIL_HOST_PASSWORD=ton_mot_de_passe_application_sans_espaces
```

(le même mot de passe d'application Gmail que tu utilises déjà en local)

## 5. Créer un compte administrateur

Le premier compte ADMIN doit être créé à la main (l'inscription publique ne
crée que des comptes CLIENT). Sur le service `cemetery-backend` → onglet
**Shell** (terminal intégré Render) :

```bash
python manage.py shell -c "
from apps.users.models import User
User.objects.create_user(username='admin', email='ton_email@gmail.com', password='UnMotDePasseSolide123!', role=User.Roles.ADMIN)
print('admin créé')
"
```

## 6. Vérifier que tout marche

1. Ouvre l'URL de `cemetery-frontend` (`https://cemetery-frontend-xxxx.onrender.com`)
2. Connecte-toi avec le compte admin créé à l'étape 5
3. Vérifie que le code MFA arrive bien par email

## À savoir avant la démo / remise

- **Palier gratuit Render** : le backend et le frontend "s'endorment" après
  15 minutes sans trafic, et mettent 30-60 secondes à se réveiller au
  premier chargement après une pause. Si tu dois démontrer le projet en
  direct, ouvre l'URL 2-3 minutes avant pour le "réveiller".
- **Base PostgreSQL gratuite** : expire après 30 jours. Largement suffisant
  pour une remise aujourd'hui, mais pas pour un usage à long terme sans
  passer sur un plan payant.
- **Carte OpenStreetMap** : nécessite que le serveur ait accès à internet
  pour charger les tuiles — c'est le cas par défaut sur Render (contrairement
  à un réseau d'entreprise/université qui pourrait bloquer certains domaines).
