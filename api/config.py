"""Centralized environment-driven configuration for the CDC API service."""

import logging
import os
from dataclasses import dataclass

_config_logger = logging.getLogger("cdc-api.config")

_INSECURE_DEFAULTS = {"change_me_secret", "change_me_api_jwt_secret_key", "secret"}


def _warn_if_insecure(name: str, value: str) -> None:
    if value.lower() in _INSECURE_DEFAULTS or len(value) < 16:
        _config_logger.warning(
            "SECURITY: %s looks like a placeholder or is too short (< 16 chars). "
            "Set a strong random value in .env before deploying.",
            name,
        )


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str
    kafka_bootstrap_servers: str
    trino_url: str
    kafka_connect_url: str
    spark_master_url: str
    spark_history_url: str
    secret_key: str
    access_token_expire_minutes: int
    admin_password: str
    cors_origins: tuple[str, ...]
    jwt_algorithm: str
    trino_user: str
    connector_name: str
    kafka_consumer_group: str

    @staticmethod
    def load() -> "Settings":
        return Settings(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@postgres:5432/ecommerce",
            ),
            kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            trino_url=os.getenv("TRINO_URL", "http://trino:8080").rstrip("/"),
            kafka_connect_url=os.getenv(
                "KAFKA_CONNECT_URL", "http://kafka-connect:8083"
            ).rstrip("/"),
            spark_master_url=os.getenv(
                "SPARK_MASTER_URL", "http://spark-master:8080"
            ).rstrip("/"),
            spark_history_url=os.getenv(
                "SPARK_HISTORY_URL", "http://spark-master:18080"
            ).rstrip("/"),
            secret_key=os.getenv("API_SECRET_KEY", "change_me_secret"),
            access_token_expire_minutes=int(
                os.getenv("API_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
            ),
            admin_password=os.getenv("API_ADMIN_PASSWORD", "admin"),
            cors_origins=tuple(
                _split_csv(
                    os.getenv(
                        "CORS_ORIGINS",
                        "http://localhost:3000,http://localhost:5173",
                    )
                )
            ),
            jwt_algorithm=os.getenv("API_JWT_ALGORITHM", "HS256"),
            trino_user=os.getenv("TRINO_USER", "api"),
            connector_name=os.getenv("CONNECTOR_NAME", "cdc-postgres"),
            kafka_consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "cdc-ui-consumer"),
        )

    def validate_security(self) -> None:
        """Emit warnings for any settings that look like insecure placeholders."""
        _warn_if_insecure("API_SECRET_KEY", self.secret_key)
        _warn_if_insecure("API_ADMIN_PASSWORD", self.admin_password)


settings = Settings.load()

# Layers -> Iceberg table prefix mapping. All tables live in iceberg.analytics.
ICEBERG_CATALOG = "iceberg"
ICEBERG_SCHEMA = "analytics"
LAYER_PREFIXES: dict[str, str] = {
    "bronze": "bronze_",
    "silver": "silver_",
    "gold": "gold_",
}

CDC_TOPICS: tuple[str, ...] = (
    "cdc.public.customers",
    "cdc.public.products",
    "cdc.public.orders",
    "cdc.public.order_items",
    "cdc.public.payments",
    "cdc.public.returns",
)
