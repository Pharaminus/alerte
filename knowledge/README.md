# Base de connaissances d'ALERTE (phase 1)

État au 7 novembre 2026. Ce dossier contient tous les documents dont les agents et le rapport ont besoin. Ils sont découpés article par article, recherchables et sourcés.

## Contenu du dossier

| Élément | Rôle | Étape du plan |
|---|---|---|
| `manifest.csv` | Liste de toutes les sources : identifiant, rôle, statut, lien, licence, qualité du texte | 1.3 |
| `docs/AE`, `docs/CM` | Textes nationaux (Émirats, Cameroun) | 1.4, 1.5 |
| `docs/GL` | Textes des autres pays (précédents) et cadres internationaux | 1.6, 1.7, 1.8 |
| `docs/ITU` | Textes de l'UIT (Y.3172, Readiness 2.0, modèle du hackathon) | 1.8 |
| `docs/CTX` | Documents de contexte, jamais utilisables comme base légale | 1.9 |
| `ocr/` | Texte des documents scannés, obtenu par Tesseract (utilisé à la place du PDF) | 1.10 |
| `text/` | Texte extrait de chaque document, avec un rapport d'extraction | 1.10 |
| `chunks.jsonl` | Articles découpés avec leurs métadonnées (2 961 morceaux) | 1.11 |
| `tags.yaml` | Mots-clés pour étiqueter les institutions et les sujets | 1.11 |
| `index/` | Index de recherche hybride (embeddings multilingues + mots-clés) | 1.12 |
| `actions.yaml` | Vocabulaire commun des actions (16 actions), relié aux lacunes G1–G10 | 1.13 |
| `mandates.csv` | Tableau des mandats : institution, action, pouvoir ou devoir, citation exacte | 1.13 |
| `precedents.csv` | Tableau des précédents : pour chaque lacune, ce que font les autres pays, avec citation exacte | 1.14 |

## Reconstruire la base

```
.venv/bin/python -m alerte.kb.ocr --all-scans  # 1.10 OCR des documents scannés (une seule fois)
.venv/bin/python -m alerte.kb.extract        # 1.10 extraction du texte
.venv/bin/python -m alerte.kb.chunk          # 1.11 découpage par article + étiquettes
.venv/bin/python -m alerte.kb.index build    # 1.12 index de recherche
.venv/bin/python -m alerte.kb.check_quotes   # vérifie chaque citation des deux tableaux
```

La commande `scripts/build_kb.sh` enchaîne les quatre dernières (l'OCR n'est à relancer que si un scan est ajouté).

## 1.1 Les besoins : les questions du scénario et les textes qui y répondent

| Question | Action | Lacune | Textes nationaux | Précédents |
|---|---|---|---|---|
| Qui émet l'avertissement, qui alerte, qui coordonne ? | issue_weather_warning, issue_public_alert, coordinate_response | G2 | CM-05, CM-06, CM-07, CM-10, CM-11, CM-21 ; AE-07, AE-08, AE-11 | GL-04, GL-08, GL-19 |
| Qui peut obliger un opérateur à diffuser, dans quel délai, à quel coût ? | order_operator_broadcast, relay_alert | G1 | CM-02, CM-03, CM-08, CM-20 ; AE-04, AE-05, AE-10 | GL-01, GL-04, GL-05, GL-17 |
| Qui valide un message rédigé par une IA ? | validate_ai_output | G3, G8 | CM-19 ; AE-02, AE-03 | GL-02, GL-06, GL-18 |
| Qui rectifie une fausse alerte, qui bloque un faux message, qui enquête ? | correct_false_alert, block_spoofed_alert, investigate_cyber_incident | G9 | CM-04 ; AE-06, AE-13 | GL-05, GL-06 |
| Qui répond des dommages ? | liability_for_harm | G6 | CM-04 ; AE-03 | GL-02, GL-04, GL-06 |
| Dans quelles langues et sur quelle couverture ? | alert_language_coverage | G7 | aucun texte trouvé | GL-05, GL-17 |
| Données de localisation et de santé en crise (extension) | — | G4, G5, G10 | CM-01, CM-18 ; AE-01, AE-09 | GL-03, GL-14, GL-16 |

## 1.2 Couverture des nœuds de Y.3172

| Nœud | Ce qu'il faut justifier | Documents |
|---|---|---|
| SRC | Provenance et licence des sources, réalisme des événements | manifest.csv, CTX-01, CM-16, AE-15 |
| C | Collecte des données en crise | CM-10, GL-19, GL-17 |
| PP | Formats et harmonisation (alerte) | GL-12 (CAP, X.1303), GL-08 |
| M | Encadrement des modèles d'IA | AE-02, AE-03, CM-19, GL-02, GL-15, GL-16, GL-18 |
| P | Règles, mandats, supervision humaine | mandates.csv, CM-02, CM-04, CM-05, CM-08, AE-06, GL-01, GL-02 (art. 14, 26) |
| D | Coordination entre institutions | CM-05, CM-10, GL-08, GL-11 |
| SINK | Accès, langues, inclusion | GL-05 (§ 10.480), GL-17 (accessibilité, langues) |
| MLFO / infrastructure | Orchestration, infrastructure, énergie | ITU-01, ITU-02, GL-09 |
| Données | Protection des données personnelles | CM-01, AE-01, GL-03, GL-14 |

## Bilan chiffré

- **64 sources** au manifeste : 46 obtenues en texte intégral officiel, 7 seulement en résumé ou source secondaire, 4 encore à obtenir (AE-13, CM-06, CM-20, GL-07), 7 introuvables après recherche manuelle (AE-04, AE-07, AE-08, AE-11, AE-14, AE-15, CM-19).
- **Par rôle (documents obtenus) :** 24 nationaux, 10 précédents étrangers, 13 internationaux, 6 de contexte.
- **2 961 morceaux** indexés. Les 4 documents scannés (CM-01, CM-09, CM-21, GL-14) ont été passés à l'OCR. Le nombre d'articles a été contrôlé sur les textes dont on connaît le total : AI Act 113/113, RGPD 99/99, code européen 127/127, loi émiratie 34/2021 74/74, loi émiratie 45/2021 30/30, loi sud-africaine 64/65.
- **Recherche :** 10 questions de test sur 10 trouvent le bon document dans les 5 premiers résultats.
- **Tableaux :** 44 lignes de mandats et 25 précédents ; les **61 citations** sont vérifiées automatiquement mot pour mot dans l'article cité.
- **Précédents :** 2 juridictions ou plus pour chaque lacune visée (G1, G2, G3, G5, G6, G7, G8, G9, G10).

## Premiers constats (à confirmer)

- **Cameroun, G1 :** aucun texte lu n'oblige les opérateurs à relayer une alerte publique. Le décret 2005/124 (CM-08, art. 58) charge un service du ministère de *définir* leur rôle et de *participer* à la coordination des alertes. La loi 2010/013 (CM-02, art. 28) ne couvre que l'acheminement gratuit des **communications d'urgence**, c'est-à-dire les appels de secours. Le décret 98/031 (CM-07, art. 3) confie bien « la diffusion de l'alerte » et « l'information du public » à l'autorité qui déclenche le plan d'urgence (préfet, gouverneur ou secrétaire général de la Présidence). Mais il ne dit **ni par quel canal ni qui le relaie**, et le comité national de crise (art. 7) ne compte ni le ministre des télécommunications ni les opérateurs. Le constat G1 reste « déduit » tant que les cahiers des charges de l'ART n'ont pas été lus.
- **Cameroun, G3 et G8 :** le décret 98/031 (art. 3(2)) n'autorise le déclenchement du plan que sur des « renseignements sûrs, ne donnant lieu à aucun doute ». Une prévision d'IA probabiliste (« 70 % ») ne peut pas remplir ce critère, et aucun texte ne dit qui la vérifie. Le risque est double : alerte bloquée, ou alerte lancée sans base claire.
- **Cameroun, état d'urgence :** la loi 90-47 permet de le proclamer en cas de « national disaster » (section 1) ; le ministre de l'Administration territoriale peut alors réquisitionner des biens et contrôler les médias audiovisuels (section 6). Ce n'est pas un outil d'alerte rapide.
- **Cameroun, G4 :** l'Observatoire national des risques, chargé de l'information sur les aléas, était « créé mais non encore totalement opérationnel » (plan de contingence 2011).
- **Cameroun, G10 (extension) :** la loi 2024/017 exige une autorisation préalable de l'Autorité de protection des données pour tout transfert à l'étranger (art. 32, sanctions aux art. 60 et 69), sans procédure d'urgence trouvée. Le rapport technique s'appuyait sur des résumés : c'est maintenant **documenté** sur le texte.
- **Émirats, G1 :** la loi télécom 3/2003 (AE-05) n'impose **aucune obligation de relayer les alertes**. Le plus proche : le Haut Comité peut donner des directives « in the interest of national security » (art. 3(3)) et la TDRA fixe les conditions de service des opérateurs (art. 14(3)). L'obligation des opérateurs semble se trouver dans une **spécification technique** de la TDRA (TS040, connue par un résumé, AE-10), pas dans la loi. Constat « déduit », confiance moyenne : la loi NCEMA (AE-07) est introuvable.
- **Émirats, G7 :** selon le résumé de la spécification TS040 (AE-10), les messages doivent être en anglais et en arabe.
- **Émirats, G5 (extension) :** la loi sur les données personnelles 45/2021 **ne s'applique pas aux entités publiques** (art. 2(2)). L'usage de données en crise par la NCEMA ou la police échappe donc à ce texte, et aucun cadre spécifique n'a été trouvé.
- **Émirats, textes introuvables :** loi NCEMA, loi sur la défense civile, page officielle UAE-Alert, norme NCEMA 7000, mandat du NCM. À présenter comme « texte non accessible publiquement », **jamais comme une lacune juridique**.
- **Émirats, G9 :** la loi 34/2021 (art. 62) permet aux autorités compétentes d'ordonner la rectification ou le blocage de contenus faux. C'est utile comme comparaison pour le Cameroun.

## Écarts relevés dans les fichiers fournis

| Fichier | Nom d'origine | Contenu réel |
|---|---|---|
| CM-07 | « Decree 98/031 on Emergency and Rescue Plans » | Rapport de la Direction de la Protection civile sur la Décennie internationale de prévention des catastrophes (vers 1998-1999), renuméroté **CM-21**. Le vrai décret 98/031 a été trouvé sur FAOLEX (FAO) et est maintenant CM-07 |
| CM-09 | « Law 90/047 on the State of Emergency » | Journal officiel bilingue contenant plusieurs lois. La colonne française a la marge gauche coupée, mais la **colonne anglaise de la loi 90-47 est complète** après OCR : c'est elle qui est citée |
| CM-08 | « Decree 2005-124 on Emergency Telecommunications » | Décret d'organisation du ministère des Postes et Télécommunications (seul l'art. 58 concerne l'urgence) ; l'article 29 manque dans le PDF |
| CM-14 | « SNIA July 2025 MINPOSTEL » | Article de presse (Investir au Cameroun) |
| CM-17 | « Gavi cholera article » | Plan environnemental et social de la Banque mondiale (HeSP-3) |
| CM-02, CM-14, CM-16 | — | Noms de fichiers avec un retour à la ligne caché, corrigés dans la copie |

Le 7 novembre, les fichiers du dossier `../documents/` ont été renommés d'après leur contenu réel (convention `ID_Titre.pdf`), et les fichiers téléchargés ensuite y ont été rangés. Les doublons et les textes hors sujet sont dans `../documents/_ecartes/`. Le corpus complet utilisé par le système reste `docs/`.

## Ce qui reste à faire

1. **Texte camerounais prioritaire :** les cahiers des charges ou décisions de l'**ART** sur les obligations des opérateurs (CM-20). C'est le dernier texte nécessaire pour confirmer G1. Le « cahier des charges » trouvé le 7 novembre était un appel d'offres de l'OIF : écarté.
2. **Encore à obtenir :** AE-13 (loi 5/2024 modifiant la loi cybercriminalité), CM-06 (décret 96/054 : la date du 12 mars 1996 est donnée par deux sources, CM-10 et CM-22), J-Alert (GL-07). Le script `scripts/import_downloads.py --dir <dossier>` reconnaît et range automatiquement les fichiers téléchargés.
3. **Liens sources** des fichiers CM fournis à renseigner.
4. **Relecture humaine** des deux tableaux. Les citations sont vérifiées automatiquement, mais l'interprétation (pouvoir, devoir, partiel) doit être confirmée par une deuxième personne : colonne `checked_by`.
5. **Tableau des mandats :** 44 lignes aujourd'hui, objectif 50 ou plus. Exploiter GL-10 (EW4All) et GL-11 (UIT, plans de télécommunications d'urgence) comme précédents internationaux.
