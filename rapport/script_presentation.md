# Script de Présentation — CDC Pipeline
## Deux présentateurs · ~10 minutes · ENSET Mohammedia

**P1 = Zakaria Elghouali**
**P2 = [Prénom Binôme]**

---

## SLIDE 1 — Titre (0:00 – 0:45)

**P1 :**
Bonjour à tous. Nous allons vous présenter aujourd'hui notre projet de module Big Data :
un pipeline de traitement de données en temps réel, basé sur l'Architecture Medallion
et le principe de Change Data Capture.

**P2 :**
Ce projet couvre toute la chaîne — de la capture des changements dans une base de données
relationnelle jusqu'à une console web de monitoring en temps réel.
Nous allons vous expliquer les choix techniques, l'architecture, et les résultats obtenus.

---

## SLIDE 2 — Sommaire (0:45 – 1:00)

**P1 :**
Voici le plan de notre présentation. Nous commencerons par la problématique,
puis l'architecture globale. Ensuite, chaque couche Medallion, l'API, le déploiement,
et enfin les résultats. Commençons.

---

## SLIDE 3 — Contexte & Problématique (1:00 – 2:00)

**P2 :**
Le problème de départ est simple mais fréquent dans les systèmes data réels.
Les pipelines ETL traditionnels fonctionnent en batch — toutes les heures, voire
toutes les nuits. Résultat : les données analytiques sont toujours en retard sur la réalité.

**P1 :**
Deuxième problème : les silos. Les bases opérationnelles — commandes, clients, paiements —
sont isolées. Il n'existe pas de vue unifiée pour faire de l'analytique.

**P2 :**
Notre solution : le Change Data Capture.
Au lieu de copier toute la base périodiquement, on capture chaque modification
— chaque INSERT, UPDATE, DELETE — au moment où elle se produit,
et on la propage en streaming vers une architecture en couches.
L'objectif : une latence bout-en-bout inférieure à 10 minutes,
avec un passage de PostgreSQL à Kafka en moins d'une seconde.

---

## SLIDE 4 — Architecture Globale (2:00 – 3:30)

**P1 :**
Voici l'architecture complète. Laissez-moi vous présenter les composants dans l'ordre du flux.

Tout commence avec PostgreSQL — notre base source, configurée en réplication logique.
Le journal de transactions WAL est activé pour exposer chaque changement.

**P2 :**
Debezium, exécuté via Kafka Connect, lit ce journal et produit un événement JSON
pour chaque opération. Ces événements sont publiés dans Apache Kafka sur six topics,
un par table source.

**P1 :**
Apache Spark consomme ces topics en mode Structured Streaming
et écrit les données dans des tables Apache Iceberg, stockées sur MinIO — notre S3 local.

**P2 :**
C'est là qu'intervient l'Architecture Medallion — trois couches successives :
Bronze pour la donnée brute, Silver pour la donnée nettoyée,
et Gold pour les agrégats métier.
Chaque couche est une table Iceberg avec garanties ACID et support du time-travel.

---

## SLIDE 5 — Couche Bronze (3:30 – 4:30)

**P1 :**
La couche Bronze, c'est l'ingestion brute. Aucune transformation — on préserve
la donnée telle qu'elle sort de Debezium, avec tous les champs de métadonnée :
l'opération, le timestamp source, l'offset Kafka.

**P2 :**
Le job Spark lit le topic Kafka, parse le JSON avec le schéma attendu,
et écrit en mode append dans une table Iceberg.
Le trigger est toutes les 30 secondes.

Nous avons six tables Bronze : customers, orders, order_items, payments, products, returns.
C'est le point d'entrée unique pour toute la donnée CDC.

---

## SLIDE 6 — Couche Silver (4:30 – 5:30)

**P2 :**
La couche Silver, c'est là où on nettoie et on structure la donnée.

Premier traitement : la déduplication. Dans un micro-batch, plusieurs événements
peuvent toucher la même clé primaire. On applique une fenêtre de partitionnement
par clé primaire, triée par horodatage WAL décroissant (`_source_ts_ms`),
et on ne conserve que la ligne `row_number = 1` — c'est-à-dire l'état le plus récent.

**P1 :**
Ensuite, le typage fort : les dates Debezium sont encodées en entiers (jours depuis
l'epoch Unix) — on les reconvertit en `DateType`. Les montants passent en `DoubleType`.
On évite ainsi les erreurs silencieuses en aval.

La gestion des suppressions est faite via une colonne `_is_deleted` booléenne,
déduite du champ `op` de Debezium — plutôt que de supprimer physiquement la ligne,
ce qui préserve l'historique complet dans la couche Silver.

**P2 :**
Les tables Silver sont partitionnées par `updated_date` — la date du traitement Silver —
ce qui permet à Trino d'élaguer les partitions anciennes lors des requêtes analytiques.

---

## SLIDE 7 — Couche Gold (5:30 – 6:30)

**P1 :**
La couche Gold, c'est la couche analytique finale.
Elle contient cinq tables d'agrégats directement consommables par des outils BI.

gold_customers : une vue 360 de chaque client — nombre de commandes,
montant total dépensé, valeur moyenne, dates première et dernière commande.

**P2 :**
gold_orders : chaque commande enrichie avec les informations client,
paiement, articles et retours associés.

gold_sales_facts : les KPIs journaliers, découpés par canal de vente,
segment client et catégorie produit.

Et deux tables de synthèse : gold_payments_summary pour les paiements
et gold_returns_summary pour les retours.

**P1 :**
Ces tables sont rafraîchies toutes les 5 minutes par un heartbeat Spark
déclenché à chaque nouveau micro-batch sur Silver.

---

## SLIDE 8 — API FastAPI & Console React (6:30 – 7:30)

**P2 :**
Pour exposer ce pipeline, nous avons développé une API REST avec FastAPI.

L'authentification est gérée par JWT — tokens signés HS256, expiration configurable.
L'endpoint /api/health sonde les cinq services du pipeline en parallèle
et retourne leur statut et latence en temps réel.

**P1 :**
/api/metrics/{layer} interroge Trino pour récupérer le nombre de lignes
et la partition la plus récente de chaque table — avec un cache de 30 secondes.

/api/events/stream est un flux Server-Sent Events qui ouvre un consommateur Kafka
dédié par connexion et pousse les événements CDC vers le navigateur sans polling.

**P2 :**
La console frontend est développée avec React 18, TypeScript et Tailwind CSS —
en thème sombre. Elle comporte six routes :
le dashboard KPI, une page par couche Medallion (Bronze, Silver, Gold),
une console SQL branchée sur Trino, et un flux d'événements CDC en temps réel via SSE.

---

## SLIDE 9 — Déploiement (7:30 – 8:15)

**P1 :**
Le déploiement est entièrement conteneurisé avec Docker Compose.
La machine hôte est une VM Oracle Cloud — 4 vCPU, 11,7 Go de RAM, Ubuntu 22.04.

Nous avons 21 services orchestrés sur un réseau bridge Docker :
PostgreSQL, Zookeeper, Kafka, Kafka Connect, un Spark Master, un Spark Worker,
MinIO avec son conteneur d'initialisation, le Hive Metastore sur MariaDB,
Trino, Apache Superset, la stack de monitoring complète — Prometheus, Grafana,
Loki, Alertmanager — l'API FastAPI et le frontend React.

**P2 :**
Le workflow de déploiement est simple :
on pousse sur GitHub, on fait un git pull sur la VM,
et un docker compose up lance ou met à jour les services modifiés.

La console est accessible en direct sur notre VM Oracle Cloud.

---

## SLIDE 10 — Résultats (8:15 – 9:00)

**P1 :**
Les résultats obtenus valident nos objectifs initiaux.

Les latences mesurées par étape : PostgreSQL vers Kafka en moins d'une seconde,
Bronze en 15 à 30 secondes, Silver entre 30 et 60 secondes,
et la couche Gold en 3 à 5 minutes.
La latence bout-en-bout totale est de 4 à 7 minutes — bien en dessous de
notre objectif de 10 minutes.

**P2 :**
Nous avons six topics Kafka actifs, dix-sept tables Iceberg réparties
sur les trois couches — 6 Bronze, 6 Silver, 5 Gold —
et la couche Gold se rafraîchit toutes les 5 minutes.

Les validations clés : Debezium capture fidèlement tous les types d'opérations,
Spark ne perd aucun message, Iceberg garantit les propriétés ACID,
et Trino interroge directement MinIO sans déplacement de données.

---

## SLIDE 11 — Conclusion (9:00 – 10:00)

**P1 :**
Pour conclure, ce projet nous a permis de construire un pipeline data complet,
de bout en bout, en appliquant des technologies utilisées en production
dans les grandes architectures data : CDC, Lakehouse, streaming.

**P2 :**
Les perspectives d'évolution sont nombreuses.
L'observabilité est déjà en place — Prometheus, Grafana, Loki et Alertmanager
tournent dans le stack. La prochaine étape naturelle est le déploiement sur
Kubernetes pour l'auto-scaling des workers Spark selon la charge.

**P1 :**
Nous envisageons également un Schema Registry Confluent pour formaliser
les contrats d'interface entre producteurs et consommateurs Kafka,
l'ajout d'une Dead Letter Queue pour tracer les événements malformés,
et l'intégration de modèles de machine learning sur la couche Gold
pour de la prédiction de churn ou de la détection de fraude.

**P2 :**
Nous vous remercions pour votre attention.

**P1 :**
Nous sommes disponibles pour répondre à vos questions.

---

## Timing résumé

| Slide | Contenu            | Durée  | Qui parle             |
|-------|--------------------|--------|-----------------------|
| 1     | Titre              | 0:45   | P1 puis P2            |
| 2     | Sommaire           | 0:15   | P1                    |
| 3     | Contexte           | 1:00   | P2 · P1 · P2          |
| 4     | Architecture       | 1:30   | P1 · P2 · P1 · P2     |
| 5     | Bronze             | 1:00   | P1 puis P2            |
| 6     | Silver             | 1:00   | P2 · P1 · P2          |
| 7     | Gold               | 1:00   | P1 · P2 · P1          |
| 8     | API & Frontend     | 1:00   | P2 · P1 · P2          |
| 9     | Déploiement        | 0:45   | P1 puis P2            |
| 10    | Résultats          | 0:45   | P1 puis P2            |
| 11    | Conclusion         | 1:00   | P1 · P2 · P1 · P2     |
| **Total** |                | **~10:00** |                   |

---

> **Conseils pratiques**
> - Ne pas lire le script mot pour mot — s'en servir comme aide-mémoire.
> - Pointer les éléments sur le slide au moment où on les cite.
> - Parler lentement pour les termes techniques : Debezium, Iceberg, WAL, Structured Streaming.
> - Prévoir 2-3 minutes supplémentaires pour les questions.
> - Se regarder mutuellement pour signaler la prise de parole sans couper.
