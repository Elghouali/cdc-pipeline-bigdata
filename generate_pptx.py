"""
Generate CDC Pipeline PPTX presentation.
Run: python generate_pptx.py
Output: rapport/CDC_Pipeline_Presentation.pptx

Speakers:
  P1 (Zakaria Elghouali) — Slides 1-5  : Titre, Sommaire, Contexte, Architecture, Bronze
  P2 ([Binome])          — Slides 6-10 : Silver, Gold, API, Deploiement, Resultats
  P1 + P2                — Slide 11    : Conclusion
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK    = RGBColor(0x1A, 0x1A, 0x1A)   # Claude-style dark
BG_CARD    = RGBColor(0x21, 0x21, 0x21)
BG_DEEP    = RGBColor(0x16, 0x16, 0x16)   # code panels
ACCENT     = RGBColor(0xCF, 0x6C, 0x4F)   # terra-cotta
PURPLE     = RGBColor(0xA7, 0x8B, 0xFA)
EMERALD    = RGBColor(0x34, 0xD3, 0x99)
AMBER      = RGBColor(0xFC, 0xD3, 0x4D)
RED        = RGBColor(0xF8, 0x71, 0x71)
BLUE       = RGBColor(0x60, 0xA5, 0xFA)
WHITE      = RGBColor(0xEC, 0xEC, 0xEC)
WHITE_DIM  = RGBColor(0x87, 0x87, 0x87)
BORDER     = RGBColor(0x33, 0x33, 0x33)
BRONZE_CLR = RGBColor(0xF5, 0x9E, 0x0B)
SILVER_CLR = RGBColor(0x9C, 0xA3, 0xAF)
GOLD_CLR   = RGBColor(0xFC, 0xD3, 0x4D)

W = Inches(13.33)
H = Inches(7.5)

P1_COLOR = ACCENT
P2_COLOR = EMERALD


# ── Helpers ────────────────────────────────────────────────────────────────────

def set_bg(slide, color=None):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color or BG_DARK


def add_rect(slide, x, y, w, h, fill_color=None, line_color=None, line_width=Pt(0)):
    shape = slide.shapes.add_shape(1, x, y, w, h)
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = line_width
    else:
        shape.line.fill.background()
    return shape


def add_label(slide, text, x, y, w, h,
              font_size=Pt(14), bold=False, color=WHITE,
              align=PP_ALIGN.LEFT, italic=False, font_name="Segoe UI"):
    txBox = slide.shapes.add_textbox(x, y, w, h)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = font_size
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font_name
    return txBox


def add_divider(slide, y, color=ACCENT):
    add_rect(slide, Inches(0.5), y, Inches(12.33), Pt(1.5), fill_color=color)


def speaker_chip(slide, label, color):
    x, y = Inches(11.8), Inches(0.18)
    bg = RGBColor(color[0] // 6, color[1] // 6, color[2] // 6)
    add_rect(slide, x, y, Inches(1.3), Inches(0.3),
             fill_color=bg, line_color=color, line_width=Pt(0.75))
    add_label(slide, label, x + Inches(0.04), y + Inches(0.02),
              Inches(1.22), Inches(0.26),
              font_size=Pt(8), bold=True, color=color, align=PP_ALIGN.CENTER)


def tag_chip(slide, text, x, y, color=ACCENT):
    bg = RGBColor(color[0] // 6, color[1] // 6, color[2] // 6)
    add_rect(slide, x, y, Inches(1.3), Inches(0.3),
             fill_color=bg, line_color=color, line_width=Pt(0.75))
    add_label(slide, text, x + Inches(0.05), y + Inches(0.02),
              Inches(1.2), Inches(0.26),
              font_size=Pt(8), bold=True, color=color, align=PP_ALIGN.CENTER)


def section_header(slide, num, title, top_color=ACCENT,
                   speaker_label=None, speaker_color=None):
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=top_color)
    if speaker_label and speaker_color:
        speaker_chip(slide, speaker_label, speaker_color)
    add_label(slide, num, Inches(0.6), Inches(0.18),
              Inches(10.8), Inches(0.38), font_size=Pt(9), bold=True, color=WHITE_DIM)
    add_label(slide, title, Inches(0.6), Inches(0.6),
              Inches(11.5), Inches(0.62), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.38), color=top_color)
    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


# ── Slides ─────────────────────────────────────────────────────────────────────

def slide_title(prs):
    """Slide 1 · P1"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=ACCENT)
    speaker_chip(slide, "P1 — Zakaria", P1_COLOR)

    add_rect(slide, Inches(0.6), Inches(0.72), Inches(2.0), Inches(0.42),
             fill_color=RGBColor(0x2A, 0x18, 0x14), line_color=ACCENT, line_width=Pt(1))
    add_label(slide, "CDC PIPELINE", Inches(0.68), Inches(0.76),
              Inches(1.9), Inches(0.34), font_size=Pt(9), bold=True, color=ACCENT)

    add_label(slide, "Architecture Medallion", Inches(0.6), Inches(1.42),
              Inches(11.5), Inches(0.92), font_size=Pt(44), bold=True, color=WHITE)
    add_label(slide, "Real-Time CDC Pipeline", Inches(0.6), Inches(2.25),
              Inches(11.5), Inches(0.92), font_size=Pt(44), bold=True, color=ACCENT)

    add_label(slide,
              "Change Data Capture  ·  Apache Kafka  ·  Apache Spark  ·  Apache Iceberg  ·  Trino  ·  MinIO",
              Inches(0.6), Inches(3.28), Inches(11.5), Inches(0.45),
              font_size=Pt(14), color=WHITE_DIM)

    add_rect(slide, Inches(0.6), Inches(4.35), Inches(12.1), Pt(1), fill_color=BORDER)
    add_label(slide, "Réalisé par :", Inches(0.6), Inches(4.58),
              Inches(5), Inches(0.3), font_size=Pt(11), color=WHITE_DIM)
    add_label(slide, "Zakaria Elghouali", Inches(0.6), Inches(4.88),
              Inches(8), Inches(0.52), font_size=Pt(24), bold=True, color=WHITE)
    add_label(slide, "ENSET Mohammedia  •  Module : Big Data  •  Année 2025–2026",
              Inches(0.6), Inches(5.45), Inches(11), Inches(0.35),
              font_size=Pt(12), color=WHITE_DIM)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=ACCENT)


def slide_plan(prs):
    """Slide 2 · P1"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "PLAN DE LA PRÉSENTATION", "Sommaire",
                   top_color=ACCENT, speaker_label="P1 — Zakaria", speaker_color=P1_COLOR)

    items = [
        ("01", "Contexte & Problématique",       ACCENT,     "P1"),
        ("02", "Architecture Globale",            PURPLE,     "P1"),
        ("03", "Couche Bronze — Ingestion CDC",   BRONZE_CLR, "P1"),
        ("04", "Couche Silver — Transformation",  SILVER_CLR, "P2"),
        ("05", "Couche Gold — Agrégation",        GOLD_CLR,   "P2"),
        ("06", "API FastAPI & Console React",     PURPLE,     "P2"),
        ("07", "Déploiement Oracle Cloud",        EMERALD,    "P2"),
        ("08", "Résultats & Validation",          ACCENT,     "P2"),
    ]
    col_w = Inches(5.8)
    for i, (num, title, color, spk) in enumerate(items):
        col, row = i % 2, i // 2
        x = Inches(0.6) + col * col_w
        y = Inches(1.58) + row * Inches(1.2)
        add_rect(slide, x, y, Inches(5.5), Inches(1.02),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(0.75))
        add_label(slide, num, x + Inches(0.18), y + Inches(0.1),
                  Inches(0.7), Inches(0.55), font_size=Pt(26), bold=True, color=color)
        add_label(slide, title, x + Inches(0.95), y + Inches(0.28),
                  Inches(4.2), Inches(0.42), font_size=Pt(13), bold=True, color=WHITE)
        sp_color = P1_COLOR if spk == "P1" else P2_COLOR
        add_label(slide, spk, x + Inches(4.55), y + Inches(0.68),
                  Inches(0.8), Inches(0.26), font_size=Pt(8), bold=True, color=sp_color)


def slide_context(prs):
    """Slide 3 · P1"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "01 — CONTEXTE", "Problématique Big Data",
                   top_color=ACCENT, speaker_label="P1 — Zakaria", speaker_color=P1_COLOR)

    blocks = [
        ("Latence élevée",
         "ETL batch toutes les heures — données analytiques toujours en retard sur la réalité",
         RED),
        ("Silos de données",
         "Bases opérationnelles isolées (commandes, clients, paiements) — aucune vue analytique unifiée",
         AMBER),
        ("Solution : CDC + Medallion",
         "Change Data Capture : PostgreSQL WAL → Kafka → Spark → Iceberg en couches Bronze / Silver / Gold",
         EMERALD),
    ]
    for i, (title, desc, color) in enumerate(blocks):
        y = Inches(1.58) + i * Inches(1.62)
        add_rect(slide, Inches(0.6), y, Inches(12.1), Inches(1.42),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1))
        add_label(slide, title, Inches(0.9), y + Inches(0.1),
                  Inches(11.5), Inches(0.45), font_size=Pt(16), bold=True, color=color)
        add_label(slide, desc, Inches(0.9), y + Inches(0.6),
                  Inches(11.5), Inches(0.72), font_size=Pt(13), color=WHITE_DIM)

    add_label(slide,
              "Objectif : WAL → Kafka < 1 s  ·  Pipeline complet end-to-end < 10 minutes",
              Inches(0.6), Inches(6.62), Inches(12.1), Inches(0.45),
              font_size=Pt(13), bold=True, color=ACCENT, align=PP_ALIGN.CENTER)


def slide_architecture(prs):
    """Slide 4 · P1"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "02 — ARCHITECTURE", "Vue d'ensemble du Pipeline (21 services)",
                   top_color=PURPLE, speaker_label="P1 — Zakaria", speaker_color=P1_COLOR)

    components = [
        ("PostgreSQL",             "Source\nWAL logique",  BLUE,    Inches(0.3)),
        ("Debezium\nKafka Connect","CDC Capture",          AMBER,   Inches(2.65)),
        ("Apache Kafka",           "Broker\n6 topics",     RED,     Inches(5.0)),
        ("Apache Spark",           "Streaming\n3 jobs",    PURPLE,  Inches(7.35)),
        ("MinIO + Iceberg",        "Lakehouse\nParquet",   EMERALD, Inches(9.7)),
    ]
    for label, role, color, x in components:
        add_rect(slide, x, Inches(1.65), Inches(2.2), Inches(2.1),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1.5))
        add_label(slide, label, x + Inches(0.05), Inches(1.82),
                  Inches(2.1), Inches(0.72),
                  font_size=Pt(12), bold=True, color=color, align=PP_ALIGN.CENTER)
        add_label(slide, role, x + Inches(0.05), Inches(2.6),
                  Inches(2.1), Inches(0.6),
                  font_size=Pt(10), color=WHITE_DIM, align=PP_ALIGN.CENTER)

    for ax in [Inches(2.45), Inches(4.8), Inches(7.15), Inches(9.5)]:
        add_label(slide, "→", ax, Inches(2.45), Inches(0.4), Inches(0.4),
                  font_size=Pt(20), bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(0.3), Inches(4.1), Inches(12.7), Pt(1), fill_color=BORDER)

    layers = [
        ("BRONZE", "Ingestion brute\n6 tables append-only",   BRONZE_CLR, Inches(0.4)),
        ("SILVER", "Dédup + typage\n6 tables MERGE INTO",     SILVER_CLR, Inches(4.6)),
        ("GOLD",   "Agrégats métier\n5 tables analytics",     GOLD_CLR,   Inches(8.8)),
    ]
    for lname, ldesc, lcolor, lx in layers:
        add_rect(slide, lx, Inches(4.28), Inches(4.0), Inches(2.9),
                 fill_color=BG_CARD, line_color=lcolor, line_width=Pt(1.5))
        add_label(slide, lname, lx + Inches(0.18), Inches(4.45),
                  Inches(3.7), Inches(0.52), font_size=Pt(22), bold=True, color=lcolor)
        add_label(slide, ldesc, lx + Inches(0.18), Inches(5.05),
                  Inches(3.7), Inches(0.65), font_size=Pt(12), color=WHITE_DIM)
        add_label(slide, "Iceberg · Parquet · Snappy",
                  lx + Inches(0.18), Inches(5.75),
                  Inches(3.7), Inches(0.32),
                  font_size=Pt(9), color=lcolor, italic=True)

    for ax in [Inches(4.35), Inches(8.55)]:
        add_label(slide, "→", ax, Inches(5.3), Inches(0.4), Inches(0.4),
                  font_size=Pt(20), bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

    add_label(slide, "Trino 435 — moteur SQL distribué sur toutes les couches Iceberg",
              Inches(0.4), Inches(7.1), Inches(12.5), Inches(0.3),
              font_size=Pt(10), color=WHITE_DIM, italic=True, align=PP_ALIGN.CENTER)


def slide_bronze(prs):
    """Slide 5 · P1"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "03 — COUCHE BRONZE", "Ingestion CDC — Données Brutes",
                   top_color=BRONZE_CLR, speaker_label="P1 — Zakaria", speaker_color=P1_COLOR)

    flow = [
        ("PostgreSQL WAL",
         "wal_level=logical via args Docker · slot de réplication géré automatiquement par Debezium"),
        ("Debezium 2.5",
         "Capture INSERT / UPDATE / DELETE → JSON {op, before, after, source.ts_ms, ts_ms}"),
        ("Kafka — 6 topics",
         "cdc.public.customers · orders · order_items · payments · products · returns"),
        ("Spark — 6 streams indép.",
         "Un stream par table · checkpoint individuel MinIO · trigger 30 s · maxOffsetsPerTrigger=10 000"),
        ("Tables Bronze Iceberg",
         "Append-only · 15 colonnes · partitionné par ingestion_date · format Parquet/Snappy"),
    ]
    for i, (step, desc) in enumerate(flow):
        y = Inches(1.58) + i * Inches(1.02)
        add_rect(slide, Inches(0.5), y + Inches(0.05),
                 Inches(0.06), Inches(0.82), fill_color=BRONZE_CLR)
        add_label(slide, step, Inches(0.75), y,
                  Inches(5.2), Inches(0.42), font_size=Pt(13), bold=True, color=BRONZE_CLR)
        add_label(slide, desc, Inches(0.75), y + Inches(0.44),
                  Inches(5.8), Inches(0.52), font_size=Pt(10), color=WHITE_DIM)

    add_rect(slide, Inches(7.2), Inches(1.55), Inches(5.7), Inches(5.6),
             fill_color=BG_DEEP, line_color=BRONZE_CLR, line_width=Pt(0.75))
    add_label(slide, "bronze_job.py — extrait", Inches(7.35), Inches(1.65),
              Inches(5.4), Inches(0.32), font_size=Pt(9), bold=True, color=BRONZE_CLR)

    code = (
        "# 6 streams independants — 1 par table\n"
        "def start_table_stream(spark, table):\n"
        "  raw = (\n"
        "    spark.readStream\n"
        "      .format('kafka')\n"
        "      .option('subscribe',\n"
        "        f'cdc.public.{table}')\n"
        "      .option('maxOffsetsPer\n"
        "               Trigger', 10_000)\n"
        "      .load()\n"
        "  )\n"
        "  valid = parsed.filter(\n"
        "    col('op').isNotNull())\n\n"
        "  valid.writeTo(\n"
        "    f'iceberg.analytics\n"
        "      .bronze_{table}_cdc'\n"
        "  ).append()\n\n"
        "[start_table_stream(spark, t)\n"
        "  for t in TABLES]\n"
        "spark.streams\n"
        "  .awaitAnyTermination()"
    )
    add_label(slide, code, Inches(7.35), Inches(2.05), Inches(5.4), Inches(5.0),
              font_size=Pt(8.5), color=WHITE_DIM, font_name="Cascadia Code")

    add_label(slide,
              "→  Je passe la parole à mon binôme pour la couche Silver.",
              Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.32),
              font_size=Pt(10), italic=True, color=WHITE_DIM)


def slide_silver(prs):
    """Slide 6 · P2"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "04 — COUCHE SILVER", "Transformation & Qualité des Données",
                   top_color=SILVER_CLR, speaker_label="P2", speaker_color=P2_COLOR)

    ops = [
        ("Déduplication par PK",
         "Window.partitionBy(pk).orderBy(_source_ts_ms DESC) — row_number=1 = état le plus récent du WAL"),
        ("Typage fort",
         "Dates Debezium = entiers (jours epoch) → DateType Spark  ·  montants → DoubleType"),
        ("Soft-delete",
         "Colonne _is_deleted BOOLEAN issue du champ op='d' — aucune suppression physique"),
        ("MERGE INTO Iceberg",
         "Upsert atomique via global_temp.{view} — INSERT / UPDATE / soft-delete en une instruction"),
        ("Partitionnement",
         "PARTITIONED BY (updated_date DATE) — pruning Trino sur les requêtes analytiques"),
    ]
    for i, (op, desc) in enumerate(ops):
        y = Inches(1.58) + i * Inches(0.98)
        add_rect(slide, Inches(0.5), y, Inches(6.2), Inches(0.9),
                 fill_color=BG_CARD, line_color=SILVER_CLR, line_width=Pt(0.75))
        add_label(slide, op, Inches(0.72), y + Inches(0.06),
                  Inches(5.8), Inches(0.38), font_size=Pt(13), bold=True, color=SILVER_CLR)
        add_label(slide, desc, Inches(0.72), y + Inches(0.46),
                  Inches(5.8), Inches(0.38), font_size=Pt(10), color=WHITE_DIM)

    add_rect(slide, Inches(7.2), Inches(1.55), Inches(5.7), Inches(5.55),
             fill_color=BG_CARD, line_color=SILVER_CLR, line_width=Pt(0.75))
    add_label(slide, "Tables Silver (6)", Inches(7.35), Inches(1.7),
              Inches(5.4), Inches(0.38), font_size=Pt(13), bold=True, color=SILVER_CLR)

    tables = [
        ("silver_customers",   "id · name · email · city · segment"),
        ("silver_orders",      "id · order_date · customer_id · status · channel"),
        ("silver_order_items", "id · order_id · product_id · quantity · unit_price"),
        ("silver_payments",    "id · order_id · method · amount · status"),
        ("silver_products",    "id · name · category · brand · price · stock_qty"),
        ("silver_returns",     "id · order_id · return_date · reason · status"),
    ]
    for i, (t, cols) in enumerate(tables):
        ty = Inches(2.22) + i * Inches(0.74)
        add_rect(slide, Inches(7.35), ty, Inches(0.06), Inches(0.58), fill_color=SILVER_CLR)
        add_label(slide, t, Inches(7.55), ty + Inches(0.02),
                  Inches(5.1), Inches(0.3), font_size=Pt(11), bold=True, color=WHITE)
        add_label(slide, cols, Inches(7.55), ty + Inches(0.34),
                  Inches(5.1), Inches(0.28), font_size=Pt(8.5), color=WHITE_DIM)


def slide_gold(prs):
    """Slide 7 · P2"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "05 — COUCHE GOLD", "Agrégats Métier — Couche Analytique",
                   top_color=GOLD_CLR, speaker_label="P2", speaker_color=P2_COLOR)

    rows = [
        ("gold_customers",
         "Customer 360",
         "total_orders · total_spent · avg_order_value · first_order_date · last_order_date"),
        ("gold_orders",
         "Commandes enrichies",
         "Jointure client + paiement + items + retours → vue complète par commande"),
        ("gold_sales_facts",
         "KPIs journaliers",
         "Par canal × segment × catégorie : CA brut/net · items vendus · taux annulation/retour"),
        ("gold_payments_summary",
         "Synthèse paiements",
         "Par méthode × mois : nb transactions · montants complétés / remboursés / en attente"),
        ("gold_returns_summary",
         "Analyse retours",
         "Par raison × mois : nb retours · taux = retours / commandes livrées ce mois"),
    ]
    for i, (name, title, cols) in enumerate(rows):
        y = Inches(1.58) + i * Inches(1.06)
        add_rect(slide, Inches(0.5), y, Inches(12.3), Inches(0.98),
                 fill_color=BG_CARD, line_color=GOLD_CLR, line_width=Pt(0.75))
        add_label(slide, name, Inches(0.72), y + Inches(0.07),
                  Inches(3.8), Inches(0.38), font_size=Pt(12), bold=True, color=GOLD_CLR)
        add_label(slide, title, Inches(4.5), y + Inches(0.07),
                  Inches(3.2), Inches(0.38), font_size=Pt(12), bold=True, color=WHITE)
        add_label(slide, cols, Inches(0.72), y + Inches(0.52),
                  Inches(11.8), Inches(0.4), font_size=Pt(10), color=WHITE_DIM)

    add_label(slide,
              "Trigger : heartbeat sur silver_orders · overwritePartitions() toutes les 5 minutes (idempotent)",
              Inches(0.5), Inches(7.02), Inches(12.3), Inches(0.35),
              font_size=Pt(11), color=GOLD_CLR, align=PP_ALIGN.CENTER, italic=True)


def slide_api_frontend(prs):
    """Slide 8 · P2"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "06 — API & FRONTEND", "FastAPI Backend  +  React Console",
                   top_color=PURPLE, speaker_label="P2", speaker_color=P2_COLOR)

    add_rect(slide, Inches(0.5), Inches(1.55), Inches(5.95), Inches(5.6),
             fill_color=BG_CARD, line_color=PURPLE, line_width=Pt(1))
    add_label(slide, "FastAPI · Python 3.11 · PyJWT · asyncpg",
              Inches(0.7), Inches(1.7),
              Inches(5.5), Inches(0.4), font_size=Pt(13), bold=True, color=PURPLE)

    api_items = [
        ("POST  /auth/login",           "JWT HS256 · bcrypt · 60 min"),
        ("GET   /api/health",           "Probe parallèle 5 services · latence ms"),
        ("GET   /api/metrics/{layer}",  "Trino row counts · cache 30 s"),
        ("POST  /api/query",            "SQL SELECT → NDJSON streamé"),
        ("GET   /api/events/stream",    "SSE · consommateur Kafka dédié / connexion"),
        ("GET   /api/connector/status", "Statut Debezium · POST /restart"),
        ("GET   /api/spark/jobs",       "Historique Spark Master"),
        ("GET   /api/alerts",           "Alertes pipeline · PATCH /ack"),
    ]
    for i, (ep, desc) in enumerate(api_items):
        iy = Inches(2.25) + i * Inches(0.62)
        add_label(slide, ep, Inches(0.75), iy,
                  Inches(3.6), Inches(0.28), font_size=Pt(9.5), bold=True,
                  color=PURPLE, font_name="Cascadia Code")
        add_label(slide, desc, Inches(0.75), iy + Inches(0.28),
                  Inches(5.5), Inches(0.28), font_size=Pt(9), color=WHITE_DIM)

    add_label(slide, "56 tests pytest · 7 routeurs couverts",
              Inches(0.7), Inches(7.0), Inches(5.5), Inches(0.3),
              font_size=Pt(9), color=EMERALD, italic=True)

    add_rect(slide, Inches(7.15), Inches(1.55), Inches(5.85), Inches(5.6),
             fill_color=BG_CARD, line_color=ACCENT, line_width=Pt(1))
    add_label(slide, "React 18 · TypeScript · Vite · Tailwind (dark)",
              Inches(7.35), Inches(1.7),
              Inches(5.5), Inches(0.4), font_size=Pt(13), bold=True, color=ACCENT)

    pages = [
        ("/dashboard", "KPIs animés · métriques Medallion · santé services"),
        ("/bronze",    "Tables Bronze · row counts · tiroir schéma latéral"),
        ("/silver",    "Tables Silver · état dédupliqué courant"),
        ("/gold",      "Tables Gold · agrégats analytiques"),
        ("/query",     "Console SQL Monaco → Trino · export CSV"),
        ("/stream",    "Flux SSE live · filtre topic/table · vue Timeline"),
    ]
    for i, (route, desc) in enumerate(pages):
        py = Inches(2.25) + i * Inches(0.74)
        add_label(slide, route, Inches(7.38), py,
                  Inches(2.4), Inches(0.3), font_size=Pt(10), bold=True,
                  color=ACCENT, font_name="Cascadia Code")
        add_label(slide, desc, Inches(7.38), py + Inches(0.32),
                  Inches(5.4), Inches(0.36), font_size=Pt(9.5), color=WHITE_DIM)


def slide_deploy(prs):
    """Slide 9 · P2"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "07 — DÉPLOIEMENT", "Oracle Cloud Infrastructure — Ubuntu 22.04",
                   top_color=EMERALD, speaker_label="P2", speaker_color=P2_COLOR)

    infra = [
        ("VM Oracle Cloud",   "4 vCPU  ·  11,7 Go RAM  ·  50 Go SSD  ·  Ubuntu 22.04 LTS", EMERALD),
        ("Docker Compose v2", "21 services · réseau bridge cdc-net · 9 volumes persistants",  ACCENT),
        ("Workflow CI/CD",    "git push → git pull VM → docker compose up -d --build",        PURPLE),
    ]
    for i, (name, desc, color) in enumerate(infra):
        y = Inches(1.58) + i * Inches(1.08)
        add_rect(slide, Inches(0.5), y, Inches(5.95), Inches(0.95),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1))
        add_label(slide, name, Inches(0.75), y + Inches(0.07),
                  Inches(5.5), Inches(0.38), font_size=Pt(14), bold=True, color=color)
        add_label(slide, desc, Inches(0.75), y + Inches(0.5),
                  Inches(5.5), Inches(0.38), font_size=Pt(10.5), color=WHITE_DIM)

    add_rect(slide, Inches(7.15), Inches(1.55), Inches(5.85), Inches(5.55),
             fill_color=BG_CARD, line_color=EMERALD, line_width=Pt(0.75))
    add_label(slide, "Services Docker (21 services)", Inches(7.32), Inches(1.7),
              Inches(5.5), Inches(0.38), font_size=Pt(13), bold=True, color=EMERALD)

    services = [
        ("PostgreSQL :5432",          "Source WAL"),
        ("Zookeeper / Kafka",         "Broker :9092"),
        ("Kafka Connect",             "Debezium CDC :8083"),
        ("Spark Master",              "Orchestrateur :7077"),
        ("Spark Worker",              "Exécuteur 1 Go RAM"),
        ("MinIO + minio-init",        "Stockage S3 :9000"),
        ("Hive Metastore + MariaDB",  "Catalogue Iceberg :9083"),
        ("Trino",                     "SQL distribué :8080"),
        ("Prometheus + Grafana",      "Métriques :9090 / :3001"),
        ("Loki + Promtail",           "Logs agrégés"),
        ("Alertmanager",              "Alertes :9093"),
        ("FastAPI",                   "API REST :8000"),
        ("React (Vite)",              "Console :3000"),
    ]
    for i, (svc, desc) in enumerate(services):
        sy = Inches(2.2) + i * Inches(0.42)
        add_label(slide, svc, Inches(7.35), sy,
                  Inches(3.4), Inches(0.28), font_size=Pt(9.5), bold=True, color=EMERALD)
        add_label(slide, desc, Inches(10.75), sy,
                  Inches(2.0), Inches(0.28), font_size=Pt(9.5), color=WHITE_DIM)

    add_label(slide,
              "JVM calibrée : Trino 2 Go heap · Spark Worker 1,5 Go · Kafka 768 Mo · Hive 700 Mo",
              Inches(0.5), Inches(7.02), Inches(6.0), Inches(0.35),
              font_size=Pt(9), color=WHITE_DIM, italic=True)


def slide_results(prs):
    """Slide 10 · P2"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    section_header(slide, "08 — RÉSULTATS", "Métriques & Performances",
                   top_color=ACCENT, speaker_label="P2", speaker_color=P2_COLOR)

    # Latency breakdown panel
    add_rect(slide, Inches(0.5), Inches(1.58), Inches(12.3), Inches(2.55),
             fill_color=BG_CARD, line_color=ACCENT, line_width=Pt(1))
    add_label(slide, "Latences mesurées end-to-end",
              Inches(0.72), Inches(1.72), Inches(12), Inches(0.38),
              font_size=Pt(13), bold=True, color=ACCENT)

    latencies = [
        ("PostgreSQL → Kafka", "< 1 s",    EMERALD),
        ("Kafka → Bronze",     "15 – 30 s", BRONZE_CLR),
        ("Bronze → Silver",    "30 – 60 s", SILVER_CLR),
        ("Silver → Gold",      "3 – 5 min", GOLD_CLR),
        ("End-to-end total",   "4 – 7 min", ACCENT),
    ]
    for i, (label, val, color) in enumerate(latencies):
        lx = Inches(0.65) + i * Inches(2.44)
        add_rect(slide, lx, Inches(2.2), Inches(2.28), Inches(0.72),
                 fill_color=BG_DEEP, line_color=color, line_width=Pt(0.75))
        add_label(slide, val, lx, Inches(2.22), Inches(2.28), Inches(0.36),
                  font_size=Pt(20), bold=True, color=color, align=PP_ALIGN.CENTER)
        add_label(slide, label, lx, Inches(2.6), Inches(2.28), Inches(0.28),
                  font_size=Pt(8.5), color=WHITE_DIM, align=PP_ALIGN.CENTER)

    add_label(slide, "Objectif initial : < 10 minutes  ✓  Atteint",
              Inches(0.72), Inches(3.95), Inches(12), Inches(0.3),
              font_size=Pt(11), bold=True, color=EMERALD, align=PP_ALIGN.CENTER)

    # Validation checks
    checks = [
        ("17 tables Iceberg",       "6 Bronze · 6 Silver · 5 Gold",              BRONZE_CLR),
        ("6 topics Kafka actifs",   "Tous types CDC capturés fidèlement",         RED),
        ("ACID Iceberg garanti",    "MERGE INTO · aucune perte de message",       SILVER_CLR),
        ("Trino sur MinIO",         "SQL direct Parquet — zéro déplacement",      PURPLE),
        ("56 tests pytest",         "7 routeurs API couverts · 0 échec",          EMERALD),
    ]
    for i, (title, desc, color) in enumerate(checks):
        cx = Inches(0.5) + (i % 3) * Inches(4.15)
        cy = Inches(4.4) + (i // 3) * Inches(1.18)
        add_rect(slide, cx, cy, Inches(3.95), Inches(1.0),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(0.75))
        add_label(slide, title, cx + Inches(0.18), cy + Inches(0.08),
                  Inches(3.6), Inches(0.38), font_size=Pt(13), bold=True, color=color)
        add_label(slide, desc, cx + Inches(0.18), cy + Inches(0.5),
                  Inches(3.6), Inches(0.38), font_size=Pt(10), color=WHITE_DIM)

    add_label(slide, "→  Je repasse la parole à Zakaria pour la conclusion.",
              Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.32),
              font_size=Pt(10), italic=True, color=WHITE_DIM)


def slide_conclusion(prs):
    """Slide 11 · P1 + P2"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=PURPLE)
    speaker_chip(slide, "P1 + P2", PURPLE)

    add_label(slide, "Conclusion & Perspectives",
              Inches(0.6), Inches(0.25), Inches(11.5), Inches(0.55),
              font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.0), color=PURPLE)

    col_w = Inches(5.75)

    # Bilan — P1
    add_rect(slide, Inches(0.5), Inches(1.2), col_w, Inches(4.05),
             fill_color=BG_CARD, line_color=EMERALD, line_width=Pt(1))
    add_label(slide, "Bilan — P1", Inches(0.72), Inches(1.35),
              Inches(5.3), Inches(0.38), font_size=Pt(14), bold=True, color=EMERALD)
    acquis = [
        "Pipeline CDC complet de bout en bout",
        "Medallion Architecture (Bronze → Silver → Gold)",
        "Iceberg ACID + time-travel sur MinIO",
        "API FastAPI sécurisée · 56 tests pytest",
        "Console React 6 routes — thème sombre",
        "Stack monitoring : Prometheus · Grafana · Loki",
    ]
    for i, a in enumerate(acquis):
        add_label(slide, f"  ·  {a}",
                  Inches(0.72), Inches(1.88) + i * Inches(0.52),
                  Inches(5.3), Inches(0.46), font_size=Pt(11), color=WHITE_DIM)

    # Perspectives — P2
    add_rect(slide, Inches(7.1), Inches(1.2), col_w, Inches(4.05),
             fill_color=BG_CARD, line_color=ACCENT, line_width=Pt(1))
    add_label(slide, "Perspectives — P2", Inches(7.32), Inches(1.35),
              Inches(5.3), Inches(0.38), font_size=Pt(14), bold=True, color=ACCENT)
    persp = [
        "Kubernetes — auto-scaling workers Spark",
        "Schema Registry Confluent — contrats API",
        "Dead Letter Queue — événements malformés",
        "ML sur Gold : churn · fraude · recommandation",
        "CI/CD GitHub Actions — lint · test · build",
        "Cache Redis — métriques multi-workers",
    ]
    for i, p in enumerate(persp):
        add_label(slide, f"  ·  {p}",
                  Inches(7.32), Inches(1.88) + i * Inches(0.52),
                  Inches(5.3), Inches(0.46), font_size=Pt(11), color=WHITE_DIM)

    # Closing banner
    add_rect(slide, Inches(0.5), Inches(5.6), Inches(12.3), Inches(1.65),
             fill_color=BG_DEEP, line_color=PURPLE, line_width=Pt(1))
    add_label(slide, "Merci pour votre attention",
              Inches(0), Inches(5.78), W, Inches(0.6),
              font_size=Pt(28), bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_label(slide,
              "Zakaria Elghouali  ·  zakariaelgouali@gmail.com  ·  ENSET Mohammedia",
              Inches(0), Inches(6.48), W, Inches(0.38),
              font_size=Pt(13), color=WHITE_DIM, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=ACCENT)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H

    slide_title(prs)
    slide_plan(prs)
    slide_context(prs)
    slide_architecture(prs)
    slide_bronze(prs)
    slide_silver(prs)
    slide_gold(prs)
    slide_api_frontend(prs)
    slide_deploy(prs)
    slide_results(prs)
    slide_conclusion(prs)

    out_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapport")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "CDC_Pipeline_Presentation.pptx")
    prs.save(out_path)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
