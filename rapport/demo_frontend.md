# Script de Démonstration — Console React CDC Pipeline

**URL :** http://84.8.218.197:3000
**Durée estimée :** 4 à 6 minutes

---

## ÉTAPE 1 — Connexion (0:00 – 0:30)

Nous allons maintenant accéder à la console opérationnelle de notre pipeline CDC.
L'interface est développée en React 18 avec TypeScript et Tailwind CSS en thème sombre.

L'accès est protégé par une authentification JWT.
Chaque connexion génère un token signé avec l'algorithme HS256, valide pendant 60 minutes.
Les mots de passe sont stockés en base de données sous forme de hash bcrypt —
aucun mot de passe en clair n'est jamais persisté.

Nous nous connectons avec le compte administrateur.

---

## ÉTAPE 2 — Dashboard KPI (0:30 – 1:30)

Nous sommes maintenant sur le dashboard principal.

En haut, quatre indicateurs clés s'affichent avec une animation de comptage au chargement :
le chiffre d'affaires total, le nombre de commandes du jour, les clients actifs, et les retours.
Chaque carte affiche une tendance — verte pour une hausse, rouge pour une baisse —
ainsi qu'une sparkline miniature qui montre l'évolution sur les derniers points.

À gauche, les trois couches Medallion sont représentées sous forme de cartes :
Bronze, Silver et Gold, chacune avec le nombre total de lignes et des barres de volume
normalisées par table. Ces données sont récupérées en temps réel depuis Trino
via l'endpoint `/api/metrics/{layer}` avec un cache de 30 secondes.

Au centre-droite, le flux Kafka affiche les événements CDC en direct.
Chaque événement est coloré selon son type : vert pour INSERT, orange pour UPDATE,
rouge pour DELETE. On voit en temps réel les changements qui se produisent
dans la base PostgreSQL source.

En bas, cinq cartes de santé affichent l'état de chaque service du pipeline :
PostgreSQL, Trino, Kafka Connect, Spark et MinIO.
Chaque service est sondé en parallèle toutes les 30 secondes
et la latence de réponse est affichée en millisecondes.

---

## ÉTAPE 3 — Couche Bronze (1:30 – 2:15)

Passons maintenant à la couche Bronze.

Cette page liste les six tables Iceberg d'ingestion brute.
Pour chaque table, on voit le nombre de lignes, la date de dernière mise à jour,
et le statut de santé.

La couche Bronze est append-only — aucune modification, aucune transformation.
Chaque événement Debezium est conservé tel quel avec l'intégralité de ses métadonnées :
l'opération CDC, le payload JSON avant et après la modification,
l'horodatage du WAL PostgreSQL, et la date d'ingestion Spark.

Si l'on clique sur une table, un tiroir latéral s'ouvre et affiche le schéma complet.
On y retrouve les 15 colonnes Bronze, notamment `op` qui contient le type d'opération,
`before_payload` et `after_payload` qui sont les états JSON de la ligne avant et après,
et `ingestion_date` qui est la colonne de partition utilisée par Trino
pour élaguer les fichiers Parquet lors des requêtes.

---

## ÉTAPE 4 — Couche Silver (2:15 – 2:50)

La couche Silver contient les mêmes six entités, mais avec un nombre de lignes différent.

Contrairement à Bronze qui accumule tous les événements,
Silver ne contient que l'état courant de chaque entité après déduplication.
Le job Spark applique une fenêtre de partitionnement par clé primaire,
triée par horodatage WAL décroissant, et ne conserve que la version la plus récente.

Les types sont forts : les dates Debezium — encodées en entiers depuis l'epoch Unix —
sont converties en DateType Spark. Les montants passent en DoubleType.

Les suppressions ne sont pas physiques. Quand un enregistrement est supprimé
dans PostgreSQL, la colonne `_is_deleted` passe à `true` dans Silver.
L'historique est ainsi toujours préservé pour l'audit et le time-travel Iceberg.

La mise à jour dans Silver se fait via un `MERGE INTO` Iceberg atomique,
qui gère en une seule instruction les insertions, mises à jour et suppressions logiques.

---

## ÉTAPE 5 — Couche Gold (2:50 – 3:20)

La couche Gold est la couche analytique finale, directement consommable par des outils BI.

Elle contient cinq tables d'agrégats métier.
`gold_customers` est une vue 360 de chaque client : nombre de commandes,
montant total dépensé, valeur moyenne par commande, dates de première et dernière commande.
`gold_orders` enrichit chaque commande avec les informations client, paiement et retours.
`gold_sales_facts` contient les KPIs journaliers segmentés par canal de vente,
segment client et catégorie produit — c'est la table centrale pour l'analyse des revenus.
`gold_payments_summary` et `gold_returns_summary` sont des synthèses mensuelles.

Ces cinq tables sont rafraîchies toutes les 5 minutes par un heartbeat Spark
déclenché à chaque nouveau micro-batch sur silver_orders.
Chaque rafraîchissement réécrit la partition du jour de manière idempotente.

---

## ÉTAPE 6 — Console SQL (3:20 – 4:30)

Voici la console SQL, branchée directement sur le moteur Trino 435.

À gauche, l'explorateur de données présente l'arborescence des tables
par couche Medallion avec leurs colonnes.

L'éditeur central utilise Monaco — le même éditeur que VS Code —
avec coloration syntaxique SQL.

Exécutons quelques requêtes analytiques sur la couche Gold.

La première requête nous donne les revenus bruts par canal de vente.
On appuie sur Ctrl+Entrée pour lancer l'exécution.
Les résultats arrivent en streaming ligne par ligne depuis Trino,
en format NDJSON via l'API FastAPI, et s'affichent dans le tableau.
Le temps d'exécution est affiché en bas.

La deuxième requête retourne les dix clients qui ont le plus dépensé sur la plateforme,
avec leur segment et leur nombre total de commandes.

La troisième requête mesure la latence CDC end-to-end en comparant
l'horodatage d'ingestion Spark avec l'horodatage WAL PostgreSQL.
On voit que la latence moyenne de passage à la couche Bronze
est bien inférieure à 30 secondes, conformément à notre objectif.

Seuls les SELECT sont autorisés. Toute instruction DDL ou DML —
DROP, CREATE, INSERT, UPDATE, DELETE — est bloquée côté API
avec une réponse HTTP 400, avant même d'atteindre Trino.

On peut télécharger les résultats en CSV en cliquant sur Export CSV.

---

## ÉTAPE 7 — Flux d'événements en temps réel (4:30 – 5:10)

Cette dernière page affiche le flux d'événements CDC en temps réel.

La connexion est établie via Server-Sent Events vers l'endpoint `/api/events/stream`.
Un consommateur Kafka est ouvert par connexion navigateur avec un identifiant de groupe unique.
Cela garantit que chaque onglet reçoit la totalité des événements
sans que Kafka les répartisse entre les connexions.

On voit défiler les événements avec leur horodatage précis, leur type d'opération,
la table source et le payload de la ligne modifiée.

On peut filtrer par topic Kafka pour ne voir que les événements d'une table spécifique,
ou utiliser la barre de recherche pour filtrer par nom de table.

Un heartbeat keep-alive est envoyé toutes les 15 secondes
pour maintenir la connexion ouverte même en l'absence d'événements.

---

## Requêtes SQL à coller dans la console

```sql
-- Revenus par canal de vente
SELECT channel,
       COUNT(*) AS nb_commandes,
       ROUND(SUM(gross_revenue), 2) AS revenu_brut
FROM iceberg.analytics.gold_sales_facts
GROUP BY channel
ORDER BY revenu_brut DESC;
```

```sql
-- Top 10 clients par dépense totale
SELECT name, segment, total_orders,
       ROUND(total_spent, 2) AS total_spent
FROM iceberg.analytics.gold_customers
WHERE total_spent > 0
ORDER BY total_spent DESC
LIMIT 10;
```

```sql
-- Latence CDC end-to-end (Bronze)
SELECT source_table,
       COUNT(*) AS nb_events,
       ROUND(AVG(
         (to_unixtime(ingestion_timestamp) * 1000 - source_ts_ms) / 1000.0
       ), 2) AS latence_moy_sec
FROM iceberg.analytics.bronze_orders_cdc
GROUP BY source_table;
```

```sql
-- Méthodes de paiement ce mois
SELECT method,
       SUM(transaction_count) AS nb_transactions,
       ROUND(SUM(total_amount), 2) AS montant_total
FROM iceberg.analytics.gold_payments_summary
WHERE payment_month = FORMAT_DATETIME(NOW(), 'yyyy-MM')
GROUP BY method
ORDER BY montant_total DESC;
```

```sql
-- Nombre de lignes par couche Medallion
SELECT 'bronze' AS layer, COUNT(*) AS rows
FROM iceberg.analytics.bronze_orders_cdc
UNION ALL
SELECT 'silver', COUNT(*) FROM iceberg.analytics.silver_orders
UNION ALL
SELECT 'gold',   COUNT(*) FROM iceberg.analytics.gold_orders;
```
