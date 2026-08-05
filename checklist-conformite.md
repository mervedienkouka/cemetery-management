# Checklist de conformité — Cahier des charges GI2 2026 (Gestion de Cimetière)

Légende : ✅ fait et testé | ⚠️ partiel / limite documentée | ❌ pas fait

## 2.1 Utilisateurs et rôles (RBAC)
- ✅ 4 rôles (Administrateur, Agent de terrain, Secrétariat, Client)
- ✅ MFA par email obligatoire (code à 6 chiffres, expire 10 min, hashé en base)
- ✅ Droits granulaires par ressource + isolation des données client
- ✅ Inscription publique (les clients créent eux-mêmes leur compte, rôle CLIENT par défaut)
- ✅ Gestion des rôles côté admin (changer le rôle, activer/désactiver un compte) via l'interface "Utilisateurs"
- ✅ Erreurs SMTP (MFA) gérées proprement : message clair au lieu d'un crash brut à l'écran

## 2.2 Terrain et inventaire
- ✅ Cimetières/Blocs/Tombes (CRUD complet depuis l'interface Flet)
- ✅ Calcul automatique du nombre de places (déduction des zones non exploitables)
- ✅ Taille standard des tombeaux configurable par cimetière

## 2.3 Cartographie interactive (SIG)
- ✅ Code couleur dynamique vert/orange/rouge/gris
- ✅ Vraie carte géographique (fond de carte OpenStreetMap réel via `flet-map`), tombes positionnées à leurs coordonnées lat/long réelles, centrée systématiquement sur Pointe-Noire (Congo-Brazzaville)
- ❌ PostGIS — abandonné volontairement (GDAL bloquant sous Windows) ; lat/long en `DecimalField` simple, ce qui suffit pour l'affichage carte (aucune requête géospatiale avancée n'était utilisée)

## 2.4 Réservation et validation
- ✅ Workflow complet : réservation → validation admin/secrétariat → tombe rouge → facture PDF générée et envoyée par email

## 2.5 Concessions et exhumations
- ✅ Concessions : CRUD + suivi de solde restant
- ✅ Exhumations : CRUD + validation administrative + PV PDF téléchargeable
- ✅ Alertes d'échéance de concession et de retard de paiement : déclenchables manuellement depuis le tableau de bord admin (bouton "Vérifier maintenant") **et** programmables via la commande `send_alerts` (cron/tâche planifiée) pour un envoi automatique quotidien

## 2.6 Gestion financière
- ✅ Mobile Money, Airtel Money, espèces, virement
- ✅ Paiements partiels + calcul du solde restant

## 3. Exigences non fonctionnelles
- ❌ Pas encore déployé (SLA/disponibilité non mesurable tant que ce n'est pas en ligne)
- ✅ Carte : chargement testé en local sans erreur (dépend d'une connexion internet pour les tuiles OpenStreetMap une fois déployé)
- ⚠️ Responsive web/desktop/mobile : Flet web fonctionne sur desktop, non testé sur mobile — hors périmètre du temps disponible aujourd'hui

## 4. Sécurité et conformité
- ✅ Mots de passe hashés, codes MFA hashés
- ✅ Audit trail immuable (testé : modification/suppression bloquées)
- ❌ TLS : à activer au niveau de l'hébergeur au moment du déploiement (pas une configuration applicative)
- ⚠️ Politique de rétention/conservation légale des registres : non automatisée dans le code (aucune purge programmée) ; à documenter dans le rapport écrit — proposition : conserver les registres de concessions et paiements pendant toute la durée légale de la concession + 10 ans après expiration/exhumation, conformément aux pratiques usuelles d'état civil, la suppression restant une action manuelle et tracée par l'audit trail (jamais de suppression automatique silencieuse d'un document légal)

## 5. Architecture technique
- ✅ Django Ninja + API RESTful (docs OpenAPI auto-générées sur `/api/docs`)
- ✅ Frontend Flet fonctionnel : accueil (KPIs colorés), login/MFA, inscription, carte réelle, réservations, terrain, concessions, paiements, exhumations, rapports, utilisateurs/rôles
- ❌ PostGIS (voir 2.3)

## 6. Notifications et alertes
- ✅ Alertes admin : nouvelle réservation, retard de paiement, seuil de saturation, échéance de concession
- ✅ Alertes client : code MFA, confirmation + facture

## 7. Reporting et statistiques
- ✅ Taux d'occupation par bloc + global, revenus par méthode de paiement
- ✅ Exports CSV (tombes, paiements)
- ✅ Export Excel : non fait (CSV seul) — le cahier des charges accepte "CSV ou Excel", donc conforme tel quel
- ✅ Dashboard visuel moderne : page d'accueil avec cartes colorées (dégradés), barres de progression par bloc, répartition des revenus par méthode — pas de bibliothèque de graphiques disponible dans cette version de Flet, donc pas de camembert/courbe animée, mais un rendu coloré et lisible

## 8. Livrables
- ❌ Lien du site déployé (à faire par l'étudiant lors de l'hébergement)
- ✅ Archive zip du code source (backend + frontend)
- ✅ Liste des modules installés (`requirements.txt` backend et frontend)

---

## Ce qu'il reste, concrètement, après cette livraison

1. **Déploiement** — le seul gros morceau qui reste : choisir un hébergement (backend Django + PostgreSQL, ex. Railway/Render ; frontend Flet packagé en web app ou hébergé séparément), configurer les variables d'environnement de production (`.env`), activer TLS côté hébergeur.
2. **Planifier `send_alerts` en tâche quotidienne** (cron sur Linux / Planificateur de tâches Windows) si une exécution automatique sans intervention est exigée — le déclenchement manuel depuis le dashboard fonctionne déjà comme filet de sécurité.
3. **Test mobile/tablette** si le cahier des charges est strict sur le "responsive" — non vérifié faute de temps.

Tout le reste (RBAC, MFA, inscription, gestion des rôles, terrain, carte réelle centrée sur Pointe-Noire, réservations, concessions, paiements, exhumations, audit, notifications, alertes, reporting CSV, dashboard coloré) est fait et testé de bout en bout dans le sandbox avant chaque livraison.
