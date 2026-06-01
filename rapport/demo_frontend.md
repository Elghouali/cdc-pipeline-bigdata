# Script de Démonstration — Console React CDC Pipeline

> **URL :** http://84.8.218.197:3000
> **Durée estimée :** 4 à 6 minutes
> **Prérequis :** pipeline complet démarré, Spark jobs actifs

---

## ÉTAPE 1 — Page de connexion (0:00 – 0:30)

**URL :** http://84.8.218.197:3000/login

**Ce qu'on fait :**
- Saisir les identifiants :
  - Username : `admin`
  - Password : `admin`
- Cliquer **Continue**

**Ce qu'on dit :**
> "L'accès est protégé par un token JWT signé HS256.
> L'authentification est gérée par FastAPI — bcrypt côté stockage."

---

## ÉTAPE 2 — Dashboard KPI (0:30 – 1:30)

**URL :** http://84.8.218.197:3000/dashboard

**Ce qu'on fait :**

1. **KPI tiles** (4 cartes en haut) :
   - Montrer les compteurs animés au chargement
   - Total Revenue · Orders Today · Active Customers · Returns
   - Pointer les flèches trend ↑ vert / ↓ rouge et les sparklines

2. **Medallion Layers** (colonne gauche) :
   - 3 cartes Bronze / Silver / Gold avec row counts
   - Barres de volume normalisées par table
   - Ces données viennent de Trino via `/api/metrics/{layer}`

3. **Kafka Events feed** (zone droite) :
   - Badges INSERT (vert) / UPDATE (orange) / DELETE (rouge)
   - Flux qui se rafraîchit automatiquement
   - Colonnes : Time · Op · Table · Payload

4. **Service Health** (bas) :
   - 5 services avec point vert = UP et latence en ms
   - Cliquer **Refresh** pour déclencher un nouveau sondage parallèle

**Ce qu'on dit :**
> "Le dashboard se rafraîchit toutes les 30 secondes.
> La santé des services est sondée en parallèle via `/api/health` —
> PostgreSQL, Trino, Kafka Connect, Spark et MinIO."

---

## ÉTAPE 3 — Bronze Layer (1:30 – 2:15)

**URL :** http://84.8.218.197:3000/bronze

**Ce qu'on fait :**

1. Montrer les 6 tables Iceberg :
   - bronze_customers_cdc · bronze_orders_cdc · bronze_order_items_cdc
   - bronze_payments_cdc · bronze_products_cdc · bronze_returns_cdc

2. **Cliquer sur `bronze_orders_cdc`** → tiroir latéral :
   - Montrer les colonnes Bronze : `kafka_key` · `op` · `before_payload`
     · `after_payload` · `source_ts_ms` · `ingestion_date`
   - Souligner que `raw_payload` conserve le JSON Debezium complet

**Ce qu'on dit :**
> "Bronze est append-only — zéro transformation.
> Chaque événement Debezium est stocké tel quel avec ses métadonnées Kafka.
> Partitionné par `ingestion_date` pour optimiser le pruning Trino."

---

## ÉTAPE 4 — Silver Layer (2:15 – 2:50)

**URL :** http://84.8.218.197:3000/silver

**Ce qu'on fait :**

1. Comparer les row counts avec Bronze
   *(Silver = état courant dédupliqué, Bronze = historique complet)*

2. **Cliquer sur `silver_orders`** → tiroir latéral :
   - Schéma typé : `id INT` · `order_date DATE` · `status STRING`
   - Colonnes métadonnées : `_op` · `_source_ts_ms` · `_updated_at` · `_is_deleted`

**Ce qu'on dit :**
> "Silver contient l'état courant après déduplication par clé primaire.
> Le `MERGE INTO` Iceberg garantit une seule ligne par entité.
> `_is_deleted = true` remplace la suppression physique — l'historique est préservé."

---

## ÉTAPE 5 — Gold Layer (2:50 – 3:20)

**URL :** http://84.8.218.197:3000/gold

**Ce qu'on fait :**

1. Montrer les 5 tables analytiques :
   - gold_customers · gold_orders · gold_sales_facts
   - gold_payments_summary · gold_returns_summary

2. **Cliquer sur `gold_sales_facts`** → tiroir latéral :
   - Colonnes : `sale_date` · `channel` · `customer_segment`
     · `product_category` · `gross_revenue` · `net_revenue`
     · `order_count` · `avg_order_value`

**Ce qu'on dit :**
> "Gold est directement consommable par des outils BI.
> Rafraîchissement toutes les 5 minutes via un heartbeat Spark sur silver_orders —
> réécriture idempotente par `overwritePartitions()`."

---

## ÉTAPE 6 — Query Console (3:20 – 4:30)

**URL :** http://84.8.218.197:3000/query

**Ce qu'on fait :**

1. Montrer le **Data Explorer** à gauche (arborescence Bronze / Silver)

2. **Requête 1 — Revenus par canal** — coller dans l'éditeur et lancer `Ctrl+Enter` :

```sql
SELECT
  channel,
  COUNT(*) AS nb_commandes,
  ROUND(SUM(gross_revenue), 2) AS revenu_brut
FROM iceberg.analytics.gold_sales_facts
GROUP BY channel
ORDER BY revenu_brut DESC
```

3. **Requête 2 — Top 10 clients** :

```sql
SELECT
  name,
  segment,
  total_orders,
  ROUND(total_spent, 2) AS total_spent
FROM iceberg.analytics.gold_customers
WHERE total_spent > 0
ORDER BY total_spent DESC
LIMIT 10
```

4. **Requête 3 — Latence CDC end-to-end** :

```sql
SELECT
  source_table,
  COUNT(*) AS nb_events,
  ROUND(AVG(
    (to_unixtime(ingestion_timestamp) * 1000 - source_ts_ms) / 1000.0
  ), 2) AS latence_moy_sec
FROM iceberg.analytics.bronze_orders_cdc
GROUP BY source_table
```

5. Cliquer **Export CSV** pour montrer le téléchargement

**Ce qu'on dit :**
> "L'éditeur Monaco tourne directement sur Trino.
> Seuls les SELECT sont autorisés — tout DDL/DML est bloqué côté API avec une réponse 400.
> Les résultats sont streamés en NDJSON ligne par ligne."

---

## ÉTAPE 7 — Event Stream (4:30 – 5:10)

**URL :** http://84.8.218.197:3000/stream

**Ce qu'on fait :**

1. Montrer le flux SSE en temps réel — événements CDC Kafka live
2. **Filtrer par topic** : sélectionner `cdc.public.orders`
3. **Rechercher** : taper `payment` dans la barre de recherche
4. Pointer les badges INSERT / UPDATE / DELETE avec timestamps précis

**Ce qu'on dit :**
> "Connexion Server-Sent Events vers `/api/events/stream`.
> Un consommateur Kafka est ouvert par connexion navigateur avec un group_id unique —
> chaque onglet reçoit 100 % des événements sans partage de charge Kafka."

---

## RÉSUMÉ

| Étape | Page              | Durée | Point clé montré                        |
|-------|-------------------|-------|-----------------------------------------|
| 1     | Login             | 0:30  | JWT auth                                |
| 2     | Dashboard         | 1:00  | KPIs + health + events feed             |
| 3     | Bronze            | 0:45  | Données brutes append-only              |
| 4     | Silver            | 0:35  | Dédup + typage fort + soft-delete       |
| 5     | Gold              | 0:30  | Agrégats métier 5 tables                |
| 6     | Query Console     | 1:10  | SQL live Trino + export CSV             |
| 7     | Event Stream      | 0:40  | SSE Kafka temps réel                    |
| **Total** |               | **~5:10** |                                     |

---

## Toutes les requêtes SQL prêtes à coller

```sql
-- 1. Revenus par canal
SELECT channel, COUNT(*) AS commandes,
       ROUND(SUM(gross_revenue), 2) AS revenu_brut
FROM iceberg.analytics.gold_sales_facts
GROUP BY channel ORDER BY revenu_brut DESC;

-- 2. Top 10 clients
SELECT name, segment, total_orders,
       ROUND(total_spent, 2) AS total_spent
FROM iceberg.analytics.gold_customers
WHERE total_spent > 0
ORDER BY total_spent DESC LIMIT 10;

-- 3. Paiements ce mois
SELECT method, SUM(transaction_count) AS nb,
       ROUND(SUM(total_amount), 2) AS montant
FROM iceberg.analytics.gold_payments_summary
WHERE payment_month = FORMAT_DATETIME(NOW(), 'yyyy-MM')
GROUP BY method ORDER BY montant DESC;

-- 4. Taux de retour par raison
SELECT reason, SUM(return_count) AS nb_retours,
       ROUND(AVG(return_rate_pct), 2) AS taux_pct
FROM iceberg.analytics.gold_returns_summary
GROUP BY reason ORDER BY nb_retours DESC;

-- 5. Latence CDC end-to-end
SELECT source_table, COUNT(*) AS events,
       ROUND(AVG((to_unixtime(ingestion_timestamp)*1000
                  - source_ts_ms) / 1000.0), 2) AS latence_moy_s
FROM iceberg.analytics.bronze_orders_cdc
GROUP BY source_table;

-- 6. Lignes par couche Medallion
SELECT 'bronze' AS layer, COUNT(*) AS rows
FROM iceberg.analytics.bronze_orders_cdc
UNION ALL
SELECT 'silver', COUNT(*) FROM iceberg.analytics.silver_orders
UNION ALL
SELECT 'gold',   COUNT(*) FROM iceberg.analytics.gold_orders;
```
