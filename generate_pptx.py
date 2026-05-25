"""
Generate CDC Pipeline PPTX presentation.
Run: python generate_pptx.py
Output: rapport/CDC_Pipeline_Presentation.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK    = RGBColor(0x03, 0x05, 0x0D)
BG_CARD    = RGBColor(0x06, 0x0A, 0x14)
CYAN       = RGBColor(0x00, 0xE5, 0xFF)
PURPLE     = RGBColor(0xA8, 0x55, 0xF7)
EMERALD    = RGBColor(0x10, 0xFF, 0xAA)
AMBER      = RGBColor(0xFB, 0xBF, 0x24)
RED        = RGBColor(0xF4, 0x3F, 0x5E)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
WHITE_DIM  = RGBColor(0x8A, 0x9B, 0xBA)
BRONZE_CLR = RGBColor(0xFB, 0xBF, 0x24)
SILVER_CLR = RGBColor(0x00, 0xE5, 0xFF)
GOLD_CLR   = RGBColor(0x10, 0xFF, 0xAA)

W = Inches(13.33)
H = Inches(7.5)


# ── Helpers ────────────────────────────────────────────────────────────────────

def set_bg(slide, color: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


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
              align=PP_ALIGN.LEFT, italic=False):
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
    run.font.name = "Segoe UI"
    return txBox


def add_divider(slide, y, color=CYAN):
    add_rect(slide, Inches(0.5), y, Inches(12.33), Pt(1.5), fill_color=color)


def tag_chip(slide, text, x, y, color=CYAN):
    bg = RGBColor(
        max(color[0] // 6, 0),
        max(color[1] // 6, 0),
        max(color[2] // 6, 0),
    )
    add_rect(slide, x, y, Inches(1.3), Inches(0.32),
             fill_color=bg, line_color=color, line_width=Pt(0.75))
    add_label(slide, text, x + Inches(0.05), y + Inches(0.02),
              Inches(1.2), Inches(0.28),
              font_size=Pt(8), bold=True, color=color, align=PP_ALIGN.CENTER)


# ── Slides ─────────────────────────────────────────────────────────────────────

def slide_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)

    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=CYAN)

    add_rect(slide, Inches(0.6), Inches(0.8), Inches(1.6), Inches(0.42),
             fill_color=RGBColor(0x00, 0x30, 0x40), line_color=CYAN, line_width=Pt(1))
    add_label(slide, "CDC PIPELINE", Inches(0.68), Inches(0.83),
              Inches(1.5), Inches(0.36), font_size=Pt(9), bold=True, color=CYAN)

    add_label(slide, "Architecture Medallion", Inches(0.6), Inches(1.55),
              Inches(11), Inches(0.9), font_size=Pt(46), bold=True, color=WHITE)
    add_label(slide, "Real-Time CDC Pipeline", Inches(0.6), Inches(2.35),
              Inches(11), Inches(0.9), font_size=Pt(46), bold=True, color=CYAN)

    add_label(slide, "Change Data Capture  ·  Kafka  ·  Spark  ·  Iceberg  ·  Trino  ·  MinIO",
              Inches(0.6), Inches(3.3), Inches(10), Inches(0.5),
              font_size=Pt(16), color=WHITE_DIM)

    add_rect(slide, Inches(0.6), Inches(4.55), Inches(11.8), Pt(1),
             fill_color=RGBColor(0x1A, 0x2A, 0x3A))
    add_label(slide, "Realise par :", Inches(0.6), Inches(4.75),
              Inches(4), Inches(0.3), font_size=Pt(11), color=WHITE_DIM)
    add_label(slide, "Zakaria Elghouali", Inches(0.6), Inches(5.05),
              Inches(6), Inches(0.45), font_size=Pt(22), bold=True, color=WHITE)
    add_label(slide, "ENSET Mohammedia  |  Module : Big Data  |  2025-2026",
              Inches(0.6), Inches(5.55), Inches(9), Inches(0.35),
              font_size=Pt(12), color=WHITE_DIM)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_plan(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=CYAN)

    add_label(slide, "PLAN DE LA PRESENTATION", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Sommaire", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4))

    items = [
        ("01", "Contexte & Problematique",      CYAN),
        ("02", "Architecture Globale",           PURPLE),
        ("03", "Couche Bronze — Ingestion CDC",  AMBER),
        ("04", "Couche Silver — Transformation", SILVER_CLR),
        ("05", "Couche Gold — Agregation",       GOLD_CLR),
        ("06", "API FastAPI & Console React",    PURPLE),
        ("07", "Deploiement Oracle Cloud",       EMERALD),
        ("08", "Resultats & Demonstration",      CYAN),
    ]

    col_w = Inches(5.8)
    for i, (num, title, color) in enumerate(items):
        col = i % 2
        row = i // 2
        x = Inches(0.6) + col * col_w
        y = Inches(1.6) + row * Inches(1.2)

        add_rect(slide, x, y, Inches(5.5), Inches(1.0),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(0.75))
        add_label(slide, num, x + Inches(0.2), y + Inches(0.1),
                  Inches(0.6), Inches(0.5), font_size=Pt(28), bold=True, color=color)
        add_label(slide, title, x + Inches(0.85), y + Inches(0.28),
                  Inches(4.5), Inches(0.45), font_size=Pt(14), bold=True, color=WHITE)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_context(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=CYAN)

    add_label(slide, "01 — CONTEXTE", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Problematique Big Data", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4))

    blocks = [
        ("Latence elevee",
         "ETL batch toutes les heures -> donnees obsoletes en production",
         RED),
        ("Silos de donnees",
         "Bases operationnelles isolees, pas de vue analytique unifiee",
         AMBER),
        ("Solution : CDC + Medallion",
         "Change Data Capture en temps reel avec architecture en couches Bronze/Silver/Gold",
         EMERALD),
    ]
    for i, (title, desc, color) in enumerate(blocks):
        y = Inches(1.6) + i * Inches(1.55)
        add_rect(slide, Inches(0.6), y, Inches(11.8), Inches(1.3),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1))
        add_label(slide, title, Inches(0.9), y + Inches(0.1),
                  Inches(11), Inches(0.42), font_size=Pt(16), bold=True, color=color)
        add_label(slide, desc, Inches(0.9), y + Inches(0.55),
                  Inches(11), Inches(0.65), font_size=Pt(13), color=WHITE_DIM)

    add_label(slide, "Objectif : pipeline de streaming bout-en-bout avec latence < 5 secondes",
              Inches(0.6), Inches(6.55), Inches(12), Inches(0.5),
              font_size=Pt(14), bold=True, color=CYAN, align=PP_ALIGN.CENTER)
    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_architecture(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=CYAN)

    add_label(slide, "02 — ARCHITECTURE", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Vue d'ensemble du Pipeline", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4))

    components = [
        ("PostgreSQL",          "Source\nOperationnelle", RGBColor(0x3B, 0x82, 0xF6), Inches(0.3)),
        ("Debezium\nKafka Connect", "CDC Capture",        AMBER,                       Inches(2.65)),
        ("Apache Kafka",         "Message Broker",        RED,                         Inches(5.0)),
        ("Apache Spark",         "Streaming ETL",         PURPLE,                      Inches(7.35)),
        ("MinIO + Iceberg",      "Data Lakehouse",        EMERALD,                     Inches(9.7)),
    ]

    for label, role, color, x in components:
        add_rect(slide, x, Inches(1.65), Inches(2.2), Inches(2.1),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1.5))
        add_label(slide, label, x + Inches(0.05), Inches(1.85),
                  Inches(2.1), Inches(0.7),
                  font_size=Pt(12), bold=True, color=color, align=PP_ALIGN.CENTER)
        add_label(slide, role, x + Inches(0.05), Inches(2.65),
                  Inches(2.1), Inches(0.6),
                  font_size=Pt(10), color=WHITE_DIM, align=PP_ALIGN.CENTER)

    for ax in [Inches(2.45), Inches(4.8), Inches(7.15), Inches(9.5)]:
        add_label(slide, "->", ax, Inches(2.45), Inches(0.4), Inches(0.4),
                  font_size=Pt(20), bold=True, color=CYAN, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(0.3), Inches(4.1), Inches(12.7), Pt(1),
             fill_color=RGBColor(0x15, 0x25, 0x35))

    layers = [
        ("BRONZE", "Ingestion brute — donnees CDC",   BRONZE_CLR, Inches(0.4)),
        ("SILVER", "Deduplication & typage",           SILVER_CLR, Inches(4.6)),
        ("GOLD",   "Agregats metier",                  GOLD_CLR,   Inches(8.8)),
    ]
    for lname, ldesc, lcolor, lx in layers:
        add_rect(slide, lx, Inches(4.3), Inches(4.0), Inches(2.85),
                 fill_color=BG_CARD, line_color=lcolor, line_width=Pt(1.5))
        add_label(slide, lname, lx + Inches(0.15), Inches(4.5),
                  Inches(3.7), Inches(0.5),
                  font_size=Pt(22), bold=True, color=lcolor)
        add_label(slide, ldesc, lx + Inches(0.15), Inches(5.1),
                  Inches(3.7), Inches(0.5),
                  font_size=Pt(12), color=WHITE_DIM)
        add_label(slide, "Apache Iceberg | Parquet | Snappy",
                  lx + Inches(0.15), Inches(5.65),
                  Inches(3.7), Inches(0.35),
                  font_size=Pt(9), color=lcolor, italic=True)

    for ax in [Inches(4.35), Inches(8.55)]:
        add_label(slide, "->", ax, Inches(5.3), Inches(0.4), Inches(0.4),
                  font_size=Pt(20), bold=True, color=CYAN, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_bronze(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=AMBER)

    add_label(slide, "03 — COUCHE BRONZE", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Ingestion CDC — Donnees Brutes", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4), color=AMBER)

    flow = [
        ("PostgreSQL WAL",          "Logical replication slot — wal_level = logical"),
        ("Debezium Connector",      "Capture INSERT / UPDATE / DELETE -> JSON + champ op"),
        ("Kafka Topics (x6)",       "cdc.public.customers | orders | payments | products..."),
        ("Spark Structured Streaming", "readStream.format('kafka') -> writeStream Iceberg"),
        ("Bronze Tables",           "bronze_customers, bronze_orders, bronze_payments..."),
    ]
    for i, (step, desc) in enumerate(flow):
        y = Inches(1.6) + i * Inches(1.02)
        add_rect(slide, Inches(0.5), y + Inches(0.05),
                 Inches(0.06), Inches(0.82), fill_color=AMBER)
        add_label(slide, step, Inches(0.75), y,
                  Inches(5.5), Inches(0.42), font_size=Pt(13), bold=True, color=AMBER)
        add_label(slide, desc, Inches(0.75), y + Inches(0.42),
                  Inches(6.0), Inches(0.52), font_size=Pt(10), color=WHITE_DIM)

    # Code panel
    add_rect(slide, Inches(7.2), Inches(1.55), Inches(5.7), Inches(5.6),
             fill_color=RGBColor(0x04, 0x08, 0x12), line_color=AMBER, line_width=Pt(0.75))
    add_label(slide, "bronze_job.py  (extrait)", Inches(7.35), Inches(1.65),
              Inches(5.4), Inches(0.35), font_size=Pt(9), bold=True, color=AMBER)

    code = (
        'kafka_df = (\n'
        '  spark.readStream\n'
        '    .format("kafka")\n'
        '    .option("kafka.bootstrap\n'
        '             .servers", "kafka:9092")\n'
        '    .option("subscribe", TOPIC)\n'
        '    .load()\n'
        ')\n\n'
        'parsed = (\n'
        '  kafka_df\n'
        '  .select(from_json(\n'
        '    col("value"), SCHEMA\n'
        '  ).alias("d"))\n'
        '  .select("d.*")\n'
        ')\n\n'
        'parsed.writeStream\\\n'
        '  .format("iceberg")\\\n'
        '  .outputMode("append")\\\n'
        '  .trigger(processingTime\n'
        '           ="30 seconds")\\\n'
        '  .toTable("iceberg.analytics\n'
        '            .bronze_customers")'
    )
    add_label(slide, code, Inches(7.35), Inches(2.1), Inches(5.4), Inches(5.0),
              font_size=Pt(8.5), color=WHITE_DIM)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=AMBER)


def slide_silver(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=SILVER_CLR)

    add_label(slide, "04 — COUCHE SILVER", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Transformation & Qualite des Donnees", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4), color=SILVER_CLR)

    ops = [
        ("Deduplication",   "window + row_number() sur _kafka_offset — elimine les doublons CDC"),
        ("Typage fort",     "CAST explicite : dates -> DateType, montants -> DoubleType"),
        ("Soft-delete",     "Colonne _is_deleted BOOLEAN issue du champ op Debezium"),
        ("Watermark",       "withWatermark('event_ts', '10 minutes') pour late data"),
        ("Partitionnement", "PARTITIONED BY (ingest_date DATE) pour pruning Trino"),
    ]
    for i, (op, desc) in enumerate(ops):
        y = Inches(1.6) + i * Inches(0.97)
        add_rect(slide, Inches(0.5), y, Inches(6.0), Inches(0.88),
                 fill_color=BG_CARD, line_color=SILVER_CLR, line_width=Pt(0.75))
        add_label(slide, op, Inches(0.7), y + Inches(0.05),
                  Inches(2.5), Inches(0.38), font_size=Pt(13), bold=True, color=SILVER_CLR)
        add_label(slide, desc, Inches(0.7), y + Inches(0.42),
                  Inches(5.7), Inches(0.42), font_size=Pt(10), color=WHITE_DIM)

    add_rect(slide, Inches(7.0), Inches(1.55), Inches(5.9), Inches(5.6),
             fill_color=BG_CARD, line_color=SILVER_CLR, line_width=Pt(0.75))
    add_label(slide, "Tables Silver produites", Inches(7.15), Inches(1.7),
              Inches(5.5), Inches(0.38), font_size=Pt(13), bold=True, color=SILVER_CLR)

    tables = [
        "silver_customers", "silver_orders", "silver_order_items",
        "silver_payments",  "silver_products", "silver_returns",
    ]
    for i, t in enumerate(tables):
        ty = Inches(2.2) + i * Inches(0.75)
        add_rect(slide, Inches(7.15), ty, Inches(0.06), Inches(0.55),
                 fill_color=SILVER_CLR)
        add_label(slide, t, Inches(7.35), ty + Inches(0.05),
                  Inches(5.3), Inches(0.45), font_size=Pt(12), color=WHITE)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_gold(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=GOLD_CLR)

    add_label(slide, "05 — COUCHE GOLD", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Agregats Metier — Couche Analytique", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4), color=GOLD_CLR)

    rows = [
        ("gold_customers",        "Customer 360",
         "total_orders, total_spent, avg_order_value, last_order_date"),
        ("gold_orders",           "Commandes enrichies",
         "Jointure client + paiement + retours -> vue complete par commande"),
        ("gold_sales_facts",      "KPIs journaliers",
         "Par canal x segment x categorie : CA brut, net, items vendus"),
        ("gold_payments_summary", "Synthese paiements",
         "Par methode x mois : completes, rembourses, en attente"),
        ("gold_returns_summary",  "Analyse retours",
         "Taux de retour par raison et mois"),
    ]

    for i, (name, title, cols) in enumerate(rows):
        y = Inches(1.6) + i * Inches(1.08)
        add_rect(slide, Inches(0.5), y, Inches(12.3), Inches(1.0),
                 fill_color=BG_CARD, line_color=GOLD_CLR, line_width=Pt(0.75))
        add_label(slide, name, Inches(0.7), y + Inches(0.07),
                  Inches(3.5), Inches(0.38), font_size=Pt(12), bold=True, color=GOLD_CLR)
        add_label(slide, title, Inches(4.0), y + Inches(0.07),
                  Inches(2.5), Inches(0.38), font_size=Pt(12), bold=True, color=WHITE)
        add_label(slide, cols, Inches(0.7), y + Inches(0.52),
                  Inches(11.8), Inches(0.42), font_size=Pt(10), color=WHITE_DIM)

    add_label(slide,
              "Trigger : heartbeat Spark Streaming sur silver_orders — refresh toutes les 5 minutes",
              Inches(0.5), Inches(7.0), Inches(12.3), Inches(0.38),
              font_size=Pt(11), color=GOLD_CLR, align=PP_ALIGN.CENTER, italic=True)
    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_api_frontend(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=PURPLE)

    add_label(slide, "06 — API & FRONTEND", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "FastAPI Backend  +  React Console", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4), color=PURPLE)

    add_rect(slide, Inches(0.5), Inches(1.55), Inches(5.9), Inches(5.65),
             fill_color=BG_CARD, line_color=PURPLE, line_width=Pt(1))
    add_label(slide, "FastAPI Backend", Inches(0.7), Inches(1.7),
              Inches(5.5), Inches(0.42), font_size=Pt(15), bold=True, color=PURPLE)

    api_items = [
        ("JWT Auth",                   "Bearer token — bcrypt + HS256"),
        ("GET /api/health",            "Probe parallele des 5 services"),
        ("GET /api/metrics/{layer}",   "Row counts Trino + cache 30s"),
        ("GET /api/query",             "SQL libre Trino — NDJSON streaming"),
        ("GET /api/events",            "Server-Sent Events — Kafka live"),
        ("GET /api/spark",             "Applications actives Spark Master"),
    ]
    for i, (ep, desc) in enumerate(api_items):
        iy = Inches(2.2) + i * Inches(0.75)
        add_label(slide, ep, Inches(0.75), iy,
                  Inches(3.0), Inches(0.32), font_size=Pt(11), bold=True, color=PURPLE)
        add_label(slide, desc, Inches(0.75), iy + Inches(0.3),
                  Inches(5.5), Inches(0.35), font_size=Pt(10), color=WHITE_DIM)

    add_rect(slide, Inches(7.0), Inches(1.55), Inches(5.9), Inches(5.65),
             fill_color=BG_CARD, line_color=CYAN, line_width=Pt(1))
    add_label(slide, "React Console (Vite + Tailwind)", Inches(7.2), Inches(1.7),
              Inches(5.5), Inches(0.42), font_size=Pt(15), bold=True, color=CYAN)

    pages = [
        ("Pipeline Health",  "Cartes par service — latence, statut, sonde"),
        ("Data Layers",      "Tabs Bronze/Silver/Gold — row counts, partitions"),
        ("KPI Dashboard",    "Bento grid — CA, commandes, clients, retours"),
        ("Overview",         "Topologie pipeline + donnees Medallion en direct"),
    ]
    for i, (page, desc) in enumerate(pages):
        py = Inches(2.2) + i * Inches(0.85)
        add_label(slide, page, Inches(7.2), py,
                  Inches(3.0), Inches(0.35), font_size=Pt(12), bold=True, color=CYAN)
        add_label(slide, desc, Inches(7.2), py + Inches(0.38),
                  Inches(5.5), Inches(0.42), font_size=Pt(10), color=WHITE_DIM)

    tags = ["React 18", "TypeScript", "Vite", "TailwindCSS", "Lucide"]
    for i, t in enumerate(tags):
        tag_chip(slide, t, Inches(7.2) + i * Inches(1.12), Inches(6.5), CYAN)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_deploy(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=EMERALD)

    add_label(slide, "07 — DEPLOIEMENT", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Oracle Cloud — VM Ubuntu 22.04", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4), color=EMERALD)

    infra = [
        ("Oracle Cloud VM",  "4 vCPU  |  24 GB RAM  |  Ubuntu 22.04 LTS",          EMERALD),
        ("Docker Compose",   "20 services orchestres — reseau interne cdc-net",      CYAN),
        ("Workflow CI/CD",   "git push -> pull VM -> docker compose up -d --build",  PURPLE),
    ]
    for i, (name, desc, color) in enumerate(infra):
        y = Inches(1.6) + i * Inches(1.12)
        add_rect(slide, Inches(0.5), y, Inches(5.9), Inches(0.95),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1))
        add_label(slide, name, Inches(0.75), y + Inches(0.07),
                  Inches(5.5), Inches(0.38), font_size=Pt(15), bold=True, color=color)
        add_label(slide, desc, Inches(0.75), y + Inches(0.5),
                  Inches(5.5), Inches(0.38), font_size=Pt(11), color=WHITE_DIM)

    add_rect(slide, Inches(7.0), Inches(1.55), Inches(5.9), Inches(5.65),
             fill_color=BG_CARD, line_color=EMERALD, line_width=Pt(0.75))
    add_label(slide, "Services Docker", Inches(7.15), Inches(1.7),
              Inches(5.5), Inches(0.38), font_size=Pt(14), bold=True, color=EMERALD)

    services = [
        ("PostgreSQL :5432",      "Base source + WAL"),
        ("Zookeeper / Kafka",     "Broker :9092"),
        ("Kafka Connect",         "Debezium CDC :8083"),
        ("Spark Master + Worker", "Streaming :7077"),
        ("Iceberg REST",          "Catalogue :8181"),
        ("MinIO",                 "Stockage S3 :9000"),
        ("Trino",                 "Moteur SQL :8080"),
        ("FastAPI",               "API REST :8000"),
        ("React (Nginx)",         "Console :3000"),
    ]
    for i, (svc, desc) in enumerate(services):
        sy = Inches(2.2) + i * Inches(0.56)
        add_label(slide, svc, Inches(7.2), sy,
                  Inches(3.2), Inches(0.32), font_size=Pt(10), bold=True, color=EMERALD)
        add_label(slide, desc, Inches(10.4), sy,
                  Inches(2.3), Inches(0.32), font_size=Pt(10), color=WHITE_DIM)

    add_label(slide, "http://84.8.218.197:3000", Inches(0.5), Inches(6.85),
              Inches(5.9), Inches(0.45), font_size=Pt(13), bold=True, color=CYAN,
              align=PP_ALIGN.CENTER)
    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_results(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=CYAN)

    add_label(slide, "08 — RESULTATS", Inches(0.6), Inches(0.25),
              Inches(10), Inches(0.4), font_size=Pt(10), bold=True, color=WHITE_DIM)
    add_label(slide, "Metriques & Performances", Inches(0.6), Inches(0.65),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.4))

    kpis = [
        ("< 3 s",  "Latence bout\nen bout",       CYAN),
        ("6",      "Topics Kafka\nactifs",          PURPLE),
        ("18+",    "Tables Iceberg\n(B+S+G)",       EMERALD),
        ("5 min",  "Refresh\ncouche Gold",          AMBER),
    ]
    for i, (val, label, color) in enumerate(kpis):
        x = Inches(0.4) + i * Inches(3.1)
        add_rect(slide, x, Inches(1.6), Inches(2.9), Inches(2.2),
                 fill_color=BG_CARD, line_color=color, line_width=Pt(1.5))
        add_label(slide, val, x, Inches(1.75), Inches(2.9), Inches(0.9),
                  font_size=Pt(40), bold=True, color=color, align=PP_ALIGN.CENTER)
        add_label(slide, label, x, Inches(2.65), Inches(2.9), Inches(0.7),
                  font_size=Pt(12), color=WHITE_DIM, align=PP_ALIGN.CENTER)

    checks = [
        "OK  CDC Debezium capture fidelement INSERT / UPDATE / DELETE depuis PostgreSQL WAL",
        "OK  Spark Structured Streaming ingere et transforme sans perte de messages",
        "OK  Apache Iceberg garantit ACID + time-travel sur les trois couches Medallion",
        "OK  Trino execute des requetes analytiques SQL sur MinIO sans deplacer les donnees",
        "OK  Console React affiche les metriques en temps reel avec authentification JWT",
    ]
    for i, c in enumerate(checks):
        y = Inches(4.1) + i * Inches(0.62)
        add_rect(slide, Inches(0.5), y, Inches(0.04), Inches(0.45), fill_color=EMERALD)
        add_label(slide, c, Inches(0.7), y, Inches(12.1), Inches(0.52),
                  font_size=Pt(12), color=WHITE)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=PURPLE)


def slide_conclusion(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, BG_DARK)
    add_rect(slide, Inches(0), Inches(0), W, Inches(0.04), fill_color=PURPLE)

    add_label(slide, "CONCLUSION & PERSPECTIVES", Inches(0.6), Inches(0.35),
              Inches(10), Inches(0.55), font_size=Pt(30), bold=True, color=WHITE)
    add_divider(slide, Inches(1.15), color=PURPLE)

    col_w = Inches(5.7)

    add_rect(slide, Inches(0.5), Inches(1.4), col_w, Inches(3.55),
             fill_color=BG_CARD, line_color=EMERALD, line_width=Pt(1))
    add_label(slide, "Ce que nous avons realise", Inches(0.7), Inches(1.55),
              Inches(5.3), Inches(0.42), font_size=Pt(14), bold=True, color=EMERALD)
    acquis = [
        "Pipeline CDC complet de bout en bout",
        "Medallion Architecture (Bronze -> Silver -> Gold)",
        "Stockage Iceberg ACID sur MinIO",
        "API FastAPI + authentification JWT",
        "Console de monitoring React en temps reel",
        "Deploiement conteneurise sur Oracle Cloud",
    ]
    for i, a in enumerate(acquis):
        add_label(slide, f"  . {a}", Inches(0.7), Inches(2.1) + i * Inches(0.47),
                  Inches(5.3), Inches(0.42), font_size=Pt(11), color=WHITE_DIM)

    add_rect(slide, Inches(7.0), Inches(1.4), col_w, Inches(3.55),
             fill_color=BG_CARD, line_color=CYAN, line_width=Pt(1))
    add_label(slide, "Perspectives", Inches(7.2), Inches(1.55),
              Inches(5.3), Inches(0.42), font_size=Pt(14), bold=True, color=CYAN)
    persp = [
        "Prometheus + Grafana — observabilite complete",
        "Apache Flink pour le traitement stateful avance",
        "Delta Lake comme alternative a Iceberg",
        "ML sur Gold : prediction churn, detection fraude",
        "Auto-scaling Spark workers (Kubernetes)",
        "Schema Registry Confluent — contrats API",
    ]
    for i, p in enumerate(persp):
        add_label(slide, f"  . {p}", Inches(7.2), Inches(2.1) + i * Inches(0.47),
                  Inches(5.3), Inches(0.42), font_size=Pt(11), color=WHITE_DIM)

    add_rect(slide, Inches(0.5), Inches(5.35), Inches(12.3), Inches(1.85),
             fill_color=RGBColor(0x04, 0x08, 0x12), line_color=PURPLE, line_width=Pt(1))
    add_label(slide, "Merci pour votre attention", Inches(0), Inches(5.6),
              Inches(13.33), Inches(0.55),
              font_size=Pt(28), bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_label(slide,
              "Zakaria Elghouali  |  zakariaelgouali@gmail.com  |  ENSET Mohammedia",
              Inches(0), Inches(6.25), Inches(13.33), Inches(0.38),
              font_size=Pt(13), color=WHITE_DIM, align=PP_ALIGN.CENTER)

    add_rect(slide, Inches(0), Inches(7.46), W, Inches(0.04), fill_color=CYAN)


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

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rapport")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "CDC_Pipeline_Presentation.pptx")
    prs.save(out_path)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
