
import logging

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure process-wide logging once, at application startup."""
    settings = get_settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logging.getLogger("app").setLevel(
        logging.DEBUG if settings.environment == "development" else logging.INFO
    )
