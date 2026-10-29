# Catalogue des courses : mode d'emploi

Le catalogue liste les grands trails de France des six prochains mois, avec leurs traces GPX prêtes à simuler. Il est mis à jour une fois par mois, à la main, après vérification.

- Pages : `pages/catalogue.html` (liste) et `pages/evenement.html?id=<événement>` (fiche).
- Données publiées : `assets/catalogue/catalogue.json`, plus les traces, photos et logos du même dossier.
- Dans le simulateur, les coureurs connectés ont un bouton « Choisir dans le catalogue » ; « Simuler cette course » ouvre `simulateur.html?catalogue=<événement>&epreuve=<course>` avec la trace, le nom, l'heure de départ et les ravitos déjà remplis.

## Le cycle du mois

1. **Le 1er du mois**, la tâche programmée « Catalogue SUM'IT : lot du mois » envoie deux fichiers : `lot-AAAA-MM.json` (pour le script) et `lot-AAAA-MM.md` (à lire). Sa consigne est dans `consigne-agent-mensuel.md`.
2. **Vérifier** chaque événement sur son site officiel, en suivant les points « à vérifier » du résumé. Corriger le JSON si besoin et passer `"statut": "a_verifier"` à `"verifie"` pour les événements confirmés.
3. **Récupérer** les traces GPX (événements des trois prochains mois), les photos et les logos, et les nommer exactement :
   - `<événement>__<course>.gpx`, par exemple `saintelyon-2026__80k.gpx` ;
   - `<événement>__photo.jpg` (jpg, png ou webp, en paysage, 1 400 px de large ou plus) ;
   - `<événement>__logo.png` (png, webp ou svg, fond transparent si possible).
   Les noms attendus sont listés dans le résumé de l'agent et dans le rapport du script. Indiquer l'auteur de la photo dans `photo_credit`.
4. **Intégrer** : déposer les fichiers dans `outils/catalogue/a-integrer/`, le lot dans `outils/catalogue/lots/`, puis lancer, depuis la racine du dépôt :
   ```bash
   python3 outils/integrer_catalogue.py --lot outils/catalogue/lots/2026-12.json
   ```
   Sans Python sous la main : envoyer le lot et les fichiers à Claude dans le projet « Appli Trail prédiction », qui lance le script et renvoie le dossier prêt à téléverser avec le rapport.
5. **Lire le rapport** (`outils/catalogue/rapports/rapport-AAAA-MM-JJ.md`). En cas d'erreur, rien n'est écrit : corriger et relancer.
6. **Téléverser** sur GitHub le contenu de `outils/catalogue/a-televerser/` (mêmes dossiers que le dépôt), de préférence sur une branche : Vercel construit un aperçu ; vérifier les fiches sur l'aperçu, puis fusionner. Supprimer du dépôt les fichiers listés dans « Fichiers à supprimer ».
7. Vider `outils/catalogue/a-integrer/` et `outils/catalogue/a-televerser/` (ils ne servent qu'au poste de travail).

Compter une dizaine de minutes par événement pour la vérification et les fichiers.

## Ce que contrôle le script

| Contrôle | Seuil | Effet |
|---|---|---|
| GPX lisible, 50 points au moins | | erreur |
| Altitudes présentes | 80 % des points au moins | erreur (simulation impossible) |
| Distance de la trace / distance annoncée | écart de plus de 5 % | point à regarder |
| | écart de plus de 20 % | erreur, avec la course qui correspond le mieux |
| D+ de la trace / D+ annoncé | écart de plus de 12 % | point à regarder |
| | écart de plus de 30 % | erreur |
| Sauts GPS de plus de 200 m | | corrigés, signalés |
| Ravitos (`<wpt>` à moins de 300 m de la trace) | | lus ; sinon repris du lot ; sinon signalé |
| Nom de fichier | | erreur avec le nom le plus proche |
| Photo petite (moins de 900 px) ou en hauteur | | point à regarder |
| Crédit photo manquant | | point à regarder |
| SVG contenant du script | | erreur |

Distance et D+ sont recalculés comme sur le serveur (médiane sur 3 points, hystérésis de 2 m) : le chiffre affiché par le simulateur sera le même. Chaque trace est réécrite proprement (une seule trace, altitudes, ravitos en `<wpt>`, sans horodatage). Les photos sont converties en WebP (1 440, 960 et 600 px de large) si Pillow est installé (`pip install Pillow`).

Le script retire aussi les événements terminés depuis plus de 7 jours et met à jour `sitemap.xml` (une adresse par fiche).

## Droits sur les images et les traces

Les traces, photos et logos appartiennent aux organisations. Avant de publier une photo ou un logo, demander l'accord de l'organisation (un courriel suffit) ou utiliser le dossier de presse quand il en autorise l'usage, et créditer l'auteur. Sans accord, laisser la photo vide : la case affiche le profil de la course. Chaque fiche renvoie vers le site officiel et précise que celui-ci fait foi.

## Format des données

Pour retirer une course d'un événement déjà publié : la mettre dans le lot avec son `id` et `"action": "retirer"`. Une course simplement absente du lot reste au catalogue.

Voir `consigne-agent-mensuel.md` (format du lot). Le script ajoute dans `catalogue.json`, pour chaque course intégrée : `gpx` (nom du fichier), `ravitos` et `trace` (distance, D+, D-, altitudes mini et maxi, boucle ou non, point de départ, profil de 80 points), et pour chaque événement `photo` et `logo`.
