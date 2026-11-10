# Scénarios (phase 2)

Exercices **fictifs** conçus pour tester la loi : chaque événement teste une action précise et la lacune attendue est écrite à l'avance, pour mesurer ensuite si le système la trouve.

| Fichier | Contenu | Étape du plan |
|---|---|---|
| `gaps.yaml` | Catalogue des lacunes G1 à G10 : question, règle de détection, actions concernées, précédents étrangers | 2.1 |
| `AE-01.yaml` | Émirats : fausse alerte à Dubaï, crue manquée dans les oueds de Hatta | 2.2, 2.3, 2.4 |
| `CM-01.yaml` | Cameroun : fausse alerte à Douala, crue manquée dans le Logone-et-Chari | 2.2, 2.3, 2.4 |
| `hydrosense.yaml` | Fiche de l'IA testée (fictive) et sa condition de validité | 2.5 |
| `roles/AE.yaml`, `roles/CM.yaml` | Fiches de rôle des 6 agents par pays, liées au tableau des mandats | 2.6 |
| `controversies.yaml` | Cas de controverse et réaction attendue | 2.7 |

**Contrôle qualité** (étapes 2.4 et 2.8), sans IA :

```
.venv/bin/python -m alerte.scenario.validate
```

Il vérifie le format, l'ordre des heures, les destinataires, les actions, les lignes de mandat citées, la cohérence entre le résultat attendu et la force des textes, l'inégalité de l'information, la présence d'une contradiction, la condition de validité d'HydroSense, la couverture des lacunes G1, G2, G3, G6, G7, G8, G9, la structure identique des deux pays et l'absence de personne réelle ou d'opérateur réel.

**Résultat attendu d'une lacune** : `gap` (aucun texte ne donne le pouvoir ou le devoir), `partial` (interdiction seule, texte non contraignant ou source secondaire), `covered` (un texte répond), `not_assessable` (texte non accessible : jamais présenté comme une lacune juridique).

**Reste à faire** : relecture par un équipier qui n'a pas écrit les scénarios, puis `reviewed_by` renseigné.
