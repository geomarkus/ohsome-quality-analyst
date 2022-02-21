"""Load config from environment variables or file and expose through globals."""

import logging
import logging.config
import os
import sys

import rpy2.rinterface_lib.callbacks
import yaml

from ohsome_quality_analyst import __version__ as oqt_version

CONFIG_PATH = os.getenv(
    "CONFIG",
    default=os.path.join(
        os.path.dirname(
            os.path.abspath(__file__),
        ),
        "config.yaml",
    ),
)


def load_config_from_file(path: str = CONFIG_PATH) -> dict:
    """Load configuration from disk."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_config_from_env() -> dict:
    db = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }
    cfg_db = {k: v for k, v in db.items() if v is not None}
    cfg_env = {
        "database": cfg_db,
        "osome_api": os.getenv("OHSOME_API"),
        "geom_size_limit": os.getenv("GEOM_SIZE_LIMIT"),
        "user_agent": os.getenv("USER_AGENT"),
    }
    return {k: v for k, v in cfg_env.items() if bool(v)}


def get_config() -> dict:
    cfg = load_config_from_file()
    # Give precedence to environment variables
    cfg.update(load_config_from_env())
    if "user_agent" not in cfg.keys():
        cfg["user_agent"] = "ohsome-quality-analyst/{}".format(oqt_version)
    assert (
        "database",
        "ohsome_api",
        "geom_size_limit",
        "user_agent",
        "datasets",
    ) not in cfg.keys()
    return cfg


def load_logging_config():
    """Read logging configuration from configuration file."""
    level = get_log_level()
    logging_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "logging.yaml"
    )
    with open(logging_path, "r") as f:
        logging_config = yaml.safe_load(f)
    logging_config["root"]["level"] = getattr(logging, level.upper())
    return logging_config


def get_log_level():
    if "pydevd" in sys.modules or "pdb" in sys.modules:
        default_level = "DEBUG"
    else:
        default_level = "INFO"
    return os.getenv("OQT_LOG_LEVEL", default=default_level)


def configure_logging() -> None:
    """Configure logging level and format."""

    class RPY2LoggingFilter(logging.Filter):  # Sensitive
        def filter(self, record):
            return " library ‘/usr/share/R/library’ contains no packages" in record.msg

    # Avoid R library contains no packages WARNING logs.
    # OQT has no dependencies on additional R libraries.
    rpy2.rinterface_lib.callbacks.logger.addFilter(RPY2LoggingFilter())
    # Avoid a huge amount of DEBUG logs from matplotlib font_manager.py
    logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
    logging.config.dictConfig(load_logging_config())
