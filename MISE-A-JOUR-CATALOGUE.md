# SUM'IT : mise à jour « Catalogue des courses » (29 octobre 2026)

Rien n'a été mis en ligne. Ce paquet contient les fichiers nouveaux ou modifiés, rangés comme dans le dépôt `sumit-web`.

## Contenu

| Fichier | Rôle |
|---|---|
| `pages/catalogue.html` | Nouvelle page : les événements à venir, une case par événement, rangés par mois, avec filtres |
| `pages/evenement.html` | Nouvelle page : la fiche d'un événement et de ses courses, bouton « Simuler cette course » |
| `js/catalogue.js` | Script partagé par les deux pages et le simulateur |
| `assets/catalogue/catalogue.json` | Le catalogue : 15 événements, 69 courses, sans trace pour l'instant |
| `pages/simulateur.html` | Bouton « Choisir dans le catalogue » (coureurs connectés) et ouverture directe d'une course |
| `index.html`, autres `pages/*.html`, `js/nav-user.js` | Lien « Courses » dans la navigation ; version des fichiers passée à `20261030` |
| `api.py` | Nouvel événement de mesure anonyme `catalogue_course` (rien d'autre) |
| `sitemap.xml` | Adresses du catalogue et de chaque fiche |
| `outils/integrer_catalogue.py` | Script d'intégration mensuelle : contrôle des GPX, images, catalogue, rapport |
| `outils/catalogue/` | Mode d'emploi (`LISEZMOI.md`), consigne de l'agent mensuel, lot de novembre, premier rapport |
| `README.md`, `DOCUMENTATION_TECHNIQUE.md` | Documentation à jour |

## Mise en ligne, en passant par un aperçu

1. Sur GitHub, dans `Jakouille971/sumit-web`, créer une branche `catalogue` (menu des branches, « Create branch »).
2. Sur cette branche : « Add file » puis « Upload files », et glisser le contenu du paquet (tous les dossiers et fichiers, sauf ce fichier-ci). GitHub garde les dossiers. Valider le commit sur la branche `catalogue`.
3. Vercel construit un aperçu de la branche (onglet Deployments, ou lien « Preview » d'une pull request). L'aperçu appelle l'API de production.
4. Vérifier sur l'aperçu :
   - le lien « Courses » apparaît dans la barre du haut, sur toutes les pages ;
   - `pages/catalogue.html` montre 15 événements de novembre à avril, filtres compris ;
   - une fiche, par exemple `pages/evenement.html?id=saintelyon-2026`, montre dates, distances et « Trace à venir » ;
   - `pages/simulateur.html?catalogue=thp-winter-2026&epreuve=w100` affiche « La trace de « W100 » n'est pas encore disponible » (normal tant qu'aucune trace n'est intégrée) ;
   - la connexion Google ramène toujours sur le site de production : le bouton « Choisir dans le catalogue », réservé aux coureurs connectés, se vérifie après la fusion.
5. Avant de fusionner, relire les fiches : toutes sont « à vérifier » (voir `outils/catalogue/rapports/rapport-2026-10-29.md`). Corriger `outils/catalogue/lots/2026-11.json` si besoin et relancer le script (ou demander à Claude de le faire), ou publier tel quel : chaque fiche renvoie au site officiel, qui fait foi.
6. Ouvrir une pull request de `catalogue` vers `main` et fusionner. Render redéploie l'API ; si ce n'est pas automatique, lancer un déploiement manuel (sans lui, l'événement de mesure `catalogue_course` est simplement ignoré).

## Ensuite

- Traces à récupérer maintenant (22) : THP Winter, SaintéLyon, Les 40 Bosses (à partir du 2 décembre), Trail hivernal du Sancy, Raidlight Winter Trail. Noms exacts dans le rapport.
- Le 1er décembre à 9 h 38, la tâche programmée « Catalogue SUM'IT : lot du mois » enverra le lot de décembre. Le cycle complet est décrit dans `outils/catalogue/LISEZMOI.md`.
