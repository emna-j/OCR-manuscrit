"""Logs structurés (JSON) avec masquage automatique des secrets.

Principes (cahier des charges §17) :
- jamais de clés API, mots de passe, tokens ou contenu sensible complet ;
- chaque entrée est un objet JSON lisible par un outil d'observabilité ;
- les horodatages sont en UTC ISO 8601.
"""
import json
import logging
import re
import sys
from datetime import datetime, timezone

# Champs dont la valeur est systématiquement masquée dans les logs.
REDACTED_FIELDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "gemini_api_key",
    "jwt_secret",
)

APP_LOGGER_NAME = "app"


class RedactingJsonFormatter(logging.Formatter):
    """Formate les logs en JSON et masque les valeurs sensibles."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._redact(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _redact(message: str) -> str:
        # Masque "champ=valeur" et "champ: valeur".
        pattern = re.compile(
            r"(?P<key>(?:"
            + "|".join(re.escape(field) for field in REDACTED_FIELDS)
            + r"))\s*[=:]\s*(?P<value>\"[^\"]*\"|\S+)",
            re.IGNORECASE,
        )
        return pattern.sub(lambda m: f"{m.group('key')}=[REDACTED]", message)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure (une seule fois) le logger applicatif en JSON sur stdout."""
    logger = logging.getLogger(APP_LOGGER_NAME)
    if not any(isinstance(h, logging.StreamHandler) and h.formatter for h in logger.handlers):
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(RedactingJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def get_logger(name: str = APP_LOGGER_NAME) -> logging.Logger:
    return logging.getLogger(name)