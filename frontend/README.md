# Frontend - Gestion de cimetière (Flet)

## Installation

```
cd frontend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Lancement

1. Démarrer d'abord le backend (voir `backend/README` ou `manage.py runserver`).
2. Vérifier `api_client.py` : `BASE_URL` doit pointer vers ton backend
   (`http://127.0.0.1:8000/api` par défaut).
3. Lancer le frontend :

```
python main.py
```

Une fenêtre/onglet navigateur s'ouvre sur l'application.

## Ce qui est couvert (MVP)

- Connexion + MFA par email (2 étapes)
- Carte des tombes (positionnement réel à partir de latitude/longitude,
  code couleur vert/orange/rouge/gris)
- Réservation d'une tombe disponible (client)
- Validation / rejet des réservations (secrétariat, admin)
- Rapports occupation + revenus (admin, secrétariat)

## Ce qui n'est PAS encore couvert (à ajouter si le temps le permet)

- Gestion des concessions / paiements / exhumations côté UI (les endpoints
  existent côté backend et sont déjà dans `api_client.py`, il manque les
  vues)
- Création de cimetières/blocs/tombes depuis l'interface (actuellement
  uniquement via l'API ou l'admin Django)
- Rafraîchissement automatique de la carte (nécessite de rappeler
  `refresh()` manuellement ou de rouvrir la vue)
