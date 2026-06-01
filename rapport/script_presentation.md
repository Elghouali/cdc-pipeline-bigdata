# Script de Présentation — CDC Pipeline
## Un présentateur par bloc · ~11 minutes · ENSET Mohammedia

**P1 = Zakaria Elghouali → Slides 1 à 6** (contexte, architecture globale, vue détaillée, Bronze)
**P2 = [Prénom Binôme] → Slides 7 à 11** (Silver/Gold, API, déploiement, résultats)
**Slide 12 → P1 + P2** (conclusion partagée)

---

## SLIDE 1 — Titre (0:00 – 0:40) · P1

**P1 :**
Bonjour à tous. Je suis Zakaria Elghouali, et avec mon binôme nous allons vous présenter
notre projet de module Big Data : un pipeline de traitement de données en temps réel,
basé sur l'Architecture Medallion et le principe de Change Data Capture.

Ce projet couvre toute la chaîne — de la capture des changements dans une base de données
relationnelle jusqu'à une console web de monitoring en temps réel, avec une latence
bout-en-bout de l'ordre de quelques minutes.

Je présenterai la problématique, l'architecture globale et les trois couches du pipeline.
Mon binôme prendra la parole à partir de la couche Silver pour vous présenter l'API,
le déploiement et les résultats.

---

## SLIDE 2 — Sommaire (0:40 – 0:55) · P1

**P1 :**
Voici le plan. Nous commencerons par la problématique,
puis l'architecture globale. J'enchaînerai avec les couches Bronze et Silver.
Mon binôme couvrira ensuite Gold, l'API, le déploiement et les résultats.
Commençons sans attendre.

---

## SLIDE 3 — Contexte & Problématique (0:55 – 2:00) · P1

**P1 :**
Le problème de départ est simple mais fréquent dans les systèmes data réels.
Les pipelines ETL traditionnels fonctionnent en batch — toutes les heures,
voire toutes les nuits. Résultat : les données analytiques sont toujours en retard
sur la réalité. Impossible de réagir à un pic de retours ou à une fraude en cours.

Deuxième problème : les silos. Les bases opérationnelles — commandes, clients,
paiements — sont isolées. Il n'existe pas de vue unifiée pour faire de l'analytique.

Notre réponse : le Change Data Capture.
Au lieu de copier toute la base périodiquement, on capture chaque modification
— chaque INSERT, UPDATE, DELETE — au moment où elle se produit,
et on la propage en streaming vers une architecture analytique en couches.
L'objectif : un passage de PostgreSQL à Kafka en moins d'une seconde,
et une latence bout-en-bout inférieure à 10 minutes.

---

## SLIDE 4 — Architecture Globale (2:00 – 3:30) · P1

**P1 :**
Voici l'architecture complète — 21 services Docker sur un réseau bridge unique.
Laissez-moi vous présenter les composants dans l'ordre du flux de données.

Tout commence avec PostgreSQL — notre base source, configurée en réplication logique.
Le paramètre `wal_level=logical` est injecté au démarrage du conteneur via des arguments
de commande, ce qui expose chaque changement dans le Write-Ahead Log.

Debezium, exécuté via Kafka Connect, lit ce WAL et produit un événement JSON structuré
pour chaque opération. Ces événements sont publiés dans Apache Kafka sur six topics,
un par table source : customers, products, orders, order\_items, payments, returns.

Apache Spark consomme ces topics en mode Structured Streaming — six streams indépendants,
un par table, chacun avec son propre répertoire de checkpoint sur MinIO.
Les données sont écrites en format Apache Iceberg, un format de table ouvert
qui garantit les transactions ACID, l'évolution de schéma et le time-travel.
Le stockage physique est MinIO, notre S3 local.

Enfin, Trino — le moteur SQL distribué — expose les trois couches Iceberg
en SQL standard via le catalogue `iceberg`, schéma `analytics`.
C'est le point d'accès unique pour l'API et la console web.

---

## SLIDE 5 — Vue Architecture Détaillée (3:30 – 4:15) · P1

**P1 :**
Voici maintenant une vue plus détaillée de la topologie complète — tous les 21 services,
regroupés en cinq couches fonctionnelles.

À gauche, la couche **Source** : PostgreSQL avec `wal_level=logical` activé via les arguments
de démarrage Docker, et une publication logique limitée aux six tables surveillées.

La couche **Ingestion** : Debezium lit le WAL et publie un événement JSON structuré
sur chaque topic Kafka — un topic par table, nommé `cdc.public.{table}`.
Les schémas JSON sont désactivés : le message est directement le payload.

Au centre, la couche **Traitement** : un Spark Master et un Worker orchestrent trois jobs
de streaming indépendants — Bronze avec un trigger de 30 secondes, Silver à 60 secondes
pour le `MERGE INTO`, et Gold à 5 minutes pour la réécriture des agrégats.

La couche **Stockage Medallion** : les fichiers Parquet sont persistés sur MinIO,
catalogués par le Hive Metastore, et structurés en 17 tables Iceberg réparties
sur les trois couches — Bronze, Silver, Gold — chacune avec sa propre colonne de partition.

Enfin, la couche **Exposition** : Trino exécute le SQL distribué sur MinIO,
FastAPI expose les 13 endpoints REST avec authentification JWT,
et la console React fournit l'interface opérationnelle en temps réel.

En bas, la stack de monitoring est transversale à toutes les couches :
Prometheus, Grafana, Loki, Alertmanager, Kafka Exporter et Postgres Exporter.

---

## SLIDE 6 — Couche Bronze (4:15 – 5:15) · P1

**P1 :**
La couche Bronze, c'est l'ingestion brute. Principe fondamental : zéro transformation.
On préserve la donnée telle qu'elle sort de Debezium — l'opération CDC, le payload
JSON complet, le timestamp WAL source, l'offset Kafka, la date d'ingestion.

Le job Spark lance six streams indépendants — un par table source.
À chaque micro-batch de 30 secondes, il parse le payload Debezium,
sépare les lignes valides des heartbeats — qui ont un champ `op` null —
journalise les lignes écartées, et écrit les lignes valides en mode append
dans une table Iceberg partitionnée par `ingestion_date`.

Ce design append-only garantit l'auditabilité complète :
on peut toujours remonter à l'état exact de la source à un instant donné.
C'est aussi la base stable sur laquelle les couches suivantes peuvent rejouer
leur traitement en cas d'incident.

Je passe maintenant la parole à mon binôme pour la couche Silver.

---

## SLIDE 7 — Couche Silver (5:15 – 6:15) · P2

**P2 :**
Merci. La couche Silver, c'est là où on structure et nettoie la donnée.

Le job Spark lit les tables Bronze en streaming continu avec un trigger de 60 secondes.
Dans chaque micro-batch, on applique d'abord la déduplication :
une fenêtre Spark partitionne les événements par clé primaire, les trie par
horodatage WAL décroissant — la colonne `_source_ts_ms` —
et ne conserve que la version la plus récente de chaque enregistrement.

Ensuite, le typage fort : les dates sortent de Debezium encodées en entiers —
jours depuis l'epoch Unix. On les reconvertit en `DateType` Spark.
Les montants passent en `DoubleType`. Ce typage explicite évite les erreurs
silencieuses dans la couche Gold.

La gestion des suppressions est faite via une colonne `_is_deleted` booléenne
déduite du champ `op` de Debezium — `d` pour delete.
On ne supprime jamais physiquement la ligne : on la marque supprimée.
Cela préserve l'historique complet et facilite le time-travel Iceberg.

L'upsert dans la table Silver se fait via un `MERGE INTO` Iceberg atomique,
qui gère en une seule instruction les insertions, mises à jour et suppressions logiques.
Les tables Silver sont partitionnées par `updated_date`.

---

## SLIDE 8 — Couche Gold (6:15 – 7:15) · P2

**P2 :**
La couche Gold, c'est la couche analytique finale — directement consommable par des outils BI.

Elle contient cinq tables d'agrégats. `gold_customers` est une vue 360 de chaque client :
nombre de commandes, montant total dépensé, valeur moyenne par commande,
dates de première et dernière commande. `gold_orders` enrichit chaque commande
avec les informations client, paiement, articles et retours associés.

`gold_sales_facts` est la table de faits journaliers : revenus bruts et nets,
volumes vendus, taux d'annulation et de retour — segmentés par canal de vente,
segment client et catégorie produit. C'est la table centrale pour les KPIs.
Enfin, deux tables de synthèse mensuelle : `gold_payments_summary` pour
la répartition par méthode de paiement, et `gold_returns_summary` pour
les taux de retour par raison.

Ces cinq tables sont rafraîchies toutes les 5 minutes par un heartbeat Spark
déclenché à chaque nouveau micro-batch sur `silver_orders`.
Chaque rafraîchissement réécrit la partition du jour en mode `overwritePartitions`,
ce qui rend l'opération idempotente.

---

## SLIDE 9 — API FastAPI & Console React (7:15 – 8:15) · P2

**P2 :**
Pour exposer ce pipeline, nous avons développé une API REST avec FastAPI en Python 3.11.

L'authentification est gérée par JWT — tokens signés HS256, 60 minutes de validité,
implémentés avec la librairie PyJWT. L'API compte 13 endpoints répartis en 7 routeurs.
`/api/health` sonde les cinq services clés en parallèle et retourne leur statut et latence.
`/api/metrics/{layer}` interroge Trino via son API HTTP et met le résultat en cache
30 secondes avec un mécanisme de coalescing pour éviter les requêtes dupliquées.
`/api/events/stream` ouvre un consommateur Kafka dédié par connexion
et pousse les événements CDC vers le navigateur en Server-Sent Events, sans polling.

La console frontend est développée avec React 18, TypeScript et Tailwind CSS en thème sombre.
Elle comporte six routes : le dashboard KPI avec métriques animées,
une page dédiée par couche Medallion — Bronze, Silver, Gold —,
une console SQL branchée directement sur Trino avec éditeur Monaco,
et le flux d'événements CDC en temps réel.

L'API est testée par une suite de 56 tests pytest couvrant les 7 routeurs.

---

## SLIDE 10 — Déploiement (8:15 – 9:00) · P2

**P2 :**
Le déploiement est entièrement conteneurisé avec Docker Compose.
La machine hôte est une VM Oracle Cloud Infrastructure — 4 vCPU,
11,7 Go de RAM, 50 Go SSD, Ubuntu 22.04.

Nous orchestrons 21 services sur un réseau bridge Docker unique `cdc-net`.
Les données persistantes sont réparties sur 9 volumes nommés.
La mémoire des JVM lourds a été soigneusement calibrée pour coexister
sur 11,7 Go : Trino à 2 Go de heap, Spark Worker à 1,5 Go,
Kafka à 768 Mo, Hive Metastore à 700 Mo.

Le workflow de déploiement est simple : on pousse sur GitHub,
on fait un `git pull` sur la VM, et un `docker compose up -d`
lance ou met à jour uniquement les services modifiés.
La console est accessible en direct sur notre VM Oracle Cloud.

---

## SLIDE 11 — Résultats (9:00 – 9:45) · P2

**P2 :**
Les résultats obtenus valident tous nos objectifs initiaux.

Sur les latences mesurées : PostgreSQL vers Kafka en moins d'une seconde,
Bronze en 15 à 30 secondes, Silver entre 30 et 60 secondes,
Gold en 3 à 5 minutes. Latence bout-en-bout totale : 4 à 7 minutes —
bien en dessous de notre objectif de 10 minutes.

Le pipeline tourne sur six topics Kafka actifs, dix-sept tables Iceberg
réparties sur les trois couches — 6 Bronze, 6 Silver, 5 Gold.

Les validations clés : Debezium capture fidèlement les quatre types d'opérations CDC,
Spark ne perd aucun message grâce aux checkpoints Iceberg sur MinIO,
Iceberg garantit les transactions ACID sur chaque MERGE INTO,
et Trino interroge directement les fichiers Parquet dans MinIO
sans déplacement de données.

Je repasse la parole à Zakaria pour la conclusion.

---

## SLIDE 12 — Conclusion (9:45 – 10:45) · P1 + P2

**P1 :**
Pour conclure, ce projet nous a permis de construire un pipeline data complet,
de bout en bout, en appliquant des technologies utilisées en production
dans les grandes architectures data : CDC par lecture de WAL, Lakehouse Iceberg,
Spark Structured Streaming, Trino, et une stack d'observabilité complète
Prometheus, Grafana, Loki et Alertmanager — déjà opérationnelle.

**P2 :**
Les perspectives naturelles sont le déploiement sur Kubernetes pour l'auto-scaling
des workers Spark, l'ajout d'un Schema Registry Confluent pour formaliser
les contrats d'interface Kafka, une Dead Letter Queue pour tracer les événements
malformés, et l'intégration de modèles de machine learning sur la couche Gold
pour de la prédiction de churn ou de la détection de fraude.

**P1 :**
Nous vous remercions pour votre attention.

**P2 :**
Nous sommes disponibles pour répondre à vos questions.

---

## Timing résumé

| Slide | Contenu                   | Durée  | Présentateur |
|-------|---------------------------|--------|--------------|
| 1     | Titre                     | 0:40   | **P1**       |
| 2     | Sommaire                  | 0:15   | **P1**       |
| 3     | Contexte                  | 1:05   | **P1**       |
| 4     | Architecture Globale      | 1:30   | **P1**       |
| 5     | Vue Architecture Détaillée| 0:45   | **P1**       |
| 6     | Bronze                    | 1:00   | **P1**       |
| 7     | Silver                    | 1:00   | **P2**       |
| 8     | Gold                      | 1:00   | **P2**       |
| 9     | API & Frontend            | 1:00   | **P2**       |
| 10    | Déploiement               | 0:45   | **P2**       |
| 11    | Résultats                 | 0:45   | **P2**       |
| 12    | Conclusion                | 1:00   | P1 + P2      |
| **Total** |                       | **~11:00** |          |

**Répartition :** P1 = slides 1–6 (~5:15) · P2 = slides 7–11 (~4:30) · Conclusion partagée (~1:00)

---

> **Conseils pratiques**
> - Ne pas lire le script mot pour mot — s'en servir comme aide-mémoire.
> - Pointer les éléments sur le slide au moment où on les cite.
> - Parler lentement pour les termes techniques : Debezium, Iceberg, WAL, Structured Streaming.
> - La transition slide 6→7 doit être fluide : P1 dit "je passe la parole", P2 enchaîne directement.
> - Prévoir 2–3 minutes supplémentaires pour les questions.
> - Slide 11 : P2 dit "je repasse la parole à Zakaria" avant slide 12.
