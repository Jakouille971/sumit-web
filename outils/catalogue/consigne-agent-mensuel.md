# Consigne de l'agent mensuel du catalogue

Cette consigne est celle de la tâche programmée « Catalogue SUM'IT : lot du mois », lancée le 1er de chaque mois à 9 h 38 (heure de Paris). Le lot de novembre 2026 ayant été préparé à la main, le lancement du 1er novembre s'arrête aussitôt (une phrase en tête de la tâche, absente d'ici) ; le premier lot automatique est celui du 1er décembre 2026. Chaque lancement démarre une session neuve : la consigne se suffit à elle-même. Pour la modifier, changer ce fichier puis recopier le texte dans la tâche programmée.

---

Tu prépares le lot mensuel du catalogue des courses de SUM'IT, un simulateur de trail (https://sumit-web-nine.vercel.app). Tu ne publies rien : tu produis deux fichiers que le responsable du site vérifie, complète avec les traces GPX, photos et logos, puis met en ligne lui-même. Écris en français, registre neutre.

## Étapes

1. Prends la date du jour (outil de date). L'horizon va du jour même au dernier jour du sixième mois qui suit (lancé le 1er décembre 2026 : du 1er décembre 2026 au 31 mai 2027). Le lot s'appelle `AAAA-MM` (mois du lancement).
2. Lis le catalogue publié : https://sumit-web-nine.vercel.app/assets/catalogue/catalogue.json (outil WebFetch, ou à défaut https://raw.githubusercontent.com/Jakouille971/sumit-web/main/assets/catalogue/catalogue.json). Note ses événements et leurs courses. S'il est inaccessible, travaille comme si le catalogue était vide et écris-le en tête du résumé.
3. Cherche les grands trails de France métropolitaine et de La Réunion de l'horizon : les 15 à 25 événements les plus en vue (participation, notoriété, étapes UTMB World Series, courses historiques), répartis sur les mois et les massifs. Repère-les sur les agrégateurs (Gotrail, Finishers, Miles Republic, ITRA, Campus) et confirme chaque information sur le site officiel quand il est accessible. Fais les recherches en parallèle, plusieurs à la fois.
4. Pour chaque événement de l'horizon :
   - absent du catalogue : `"action": "ajouter"`, fiche complète ;
   - déjà au catalogue : vérifie dates, distances, D+, jours, horaires, lieux, inscriptions et publication des traces ; propose `"action": "modifier"` avec seulement l'identifiant et les champs qui changent (pour une course, son `id` et les champs modifiés) ; s'il n'y a rien à changer, ne le mets pas dans le lot ;
   - annulé : `"action": "retirer"`, avec la raison dans `a_verifier`.
   Les événements passés sont retirés par le script : inutile de les proposer.
5. Règles de contenu :
   - courses solo chronométrées de 10 km et plus ; pas de relais, de courses enfants ni de randonnées non chronométrées ;
   - identifiants : minuscules, chiffres et tirets ; événement `<nom-court>-<année>` (`saintelyon-2026`), course `<distance>k` (`80k`) ou nom court (`w100`) ; un identifiant déjà publié ne change jamais ;
   - description : deux ou trois phrases factuelles écrites par toi, jamais copiées : le lieu, le terrain, ce qui distingue la course, sans superlatif publicitaire ;
   - n'invente rien. Une information inconnue vaut `null` et devient un point de `a_verifier`. Deux sources en désaccord : garde la plus officielle ou la plus récente, et écris l'autre valeur dans `a_verifier`. Un horaire repris d'une édition précédente reste à `null`, l'ancien horaire va dans `a_verifier` ;
   - date dont seul le mois est connu : `"date_debut": "AAAA-MM"`, `"date_fin": null`, `"date_confirmee": false` ;
   - `statut` vaut toujours `"a_verifier"` : seul le responsable le passe à `"verifie"`.
6. Traces : pour les événements des trois prochains mois, indique dans le résumé où trouver chaque trace (page officielle, Tracedetrail, Openrunner, Visorando, etc.) et, si l'organisation l'annonce, la date de publication dans `gpx_disponible_le`.
7. Produis deux fichiers dans le dossier de travail :
   - `lot-AAAA-MM.json`, au format ci-dessous ;
   - `lot-AAAA-MM.md`, le résumé à lire : en tête, le nombre d'événements ajoutés, modifiés, retirés, puis les trois vérifications les plus urgentes ; ensuite, mois par mois, un tableau Événement | Dates | Lieu | Courses (distance, D+, jour, horaire) | Points à vérifier ; enfin la liste des fichiers à récupérer, avec leurs noms exacts (`<id>__<course>.gpx`, `<id>__photo.jpg`, `<id>__logo.png`) et le lien où les trouver, sous forme de cases à cocher. Ajoute une partie « À surveiller » pour les événements importants dont l'édition n'est pas encore annoncée (ils n'entrent pas dans le JSON). Termine par la liste des sources.
8. Vérifie le JSON avec Python : il se lit, chaque identifiant a le bon format, chaque date est au format ISO, chaque course a `id`, `nom` et `distance_km`, aucun identifiant de course en double dans un événement.
9. Livraison : envoie les deux fichiers avec SendUserFile (statut proactive). Si l'outil Projects est disponible, enregistre aussi `lot-AAAA-MM.md` dans le projet, au chemin `claude/catalogue/lot-AAAA-MM.md`. Termine par un message de cinq lignes au plus : ce qui a changé, les vérifications urgentes, les traces à récupérer en premier.

## Format de `lot-AAAA-MM.json`

Exemple de forme seulement : les valeurs ci-dessous sont des illustrations, pas des informations à reprendre.

```json
{
  "lot": "2026-12",
  "genere_le": "2026-12-01",
  "horizon": { "du": "2026-12-01", "au": "2027-05-31" },
  "evenements": [
    {
      "id": "saintelyon-2026",
      "action": "ajouter",
      "statut": "a_verifier",
      "nom": "SaintéLyon",
      "commune": "Lyon",
      "departement": "69",
      "region": "Auvergne-Rhône-Alpes",
      "date_debut": "2026-11-28",
      "date_fin": "2026-11-29",
      "date_confirmee": true,
      "description": "Deux ou trois phrases factuelles.",
      "site_officiel": "https://www.saintelyon.com/",
      "inscription_url": null,
      "inscriptions": "complet",
      "gpx_disponible_le": null,
      "photo_credit": null,
      "courses": [
        {
          "id": "80k",
          "nom": "SaintéLyon",
          "distance_km": 80,
          "dplus_m": 2400,
          "jour": "2026-11-28",
          "heure_depart": null,
          "depart": "Saint-Étienne",
          "arrivee": "Lyon, Halle Tony Garnier",
          "ravitos": [ { "km": 21.5, "nom": "Nom du ravitaillement" } ]
        }
      ],
      "sources": [ { "titre": "Site officiel", "url": "https://www.saintelyon.com/" } ],
      "a_verifier": [ "Heure de départ 2026 non publiée (23 h 30 en 2025)." ]
    }
  ]
}
```

Valeurs permises : `inscriptions` = `ouvertes`, `bientot`, `complet`, `closes` ou `null` ; `heure_depart` = `HH:MM` ou `null` ; `jour` = `AAAA-MM-JJ` ou `null` ; `dplus_m` = nombre ou `null`. `ravitos` est facultatif : à remplir seulement si l'organisation publie la liste des ravitaillements avec leurs kilomètres (le script les place sur la trace quand le GPX n'en contient pas).
