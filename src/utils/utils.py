# utils.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_FILE = "logs/app.log"


def log_info(msg: str):
    """Лог на уровне INFO."""
    logger = logging.getLogger()
    logger.info(msg)


def log_warning(msg: str):
    """Лог на уровне WARNING."""
    logger = logging.getLogger()
    logger.warning(msg)


def log_error(msg: str):
    """Лог на уровне ERROR."""
    logger = logging.getLogger()
    logger.error(msg)


def log_debug(msg: str):
    """Лог на уровне DEBUG."""
    logger = logging.getLogger()
    logger.debug(msg)


def setup_logger(debug: bool = False):
    """
    Инициализирует логгер для приложения.
    
    :param debug: Если True, будет DEBUG, иначе INFO.
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger()
    logger.handlers = []  # Удаляем все старые хендлеры

    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Ротация лог-файла
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10_000_000,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Пример настройки подробных логов для AutoGluon (при необходимости)
    # logging.getLogger("autogluon").setLevel(logging.DEBUG)
    # logging.getLogger("autogluon.core").setLevel(logging.DEBUG)
    # logging.getLogger("autogluon.tabular").setLevel(logging.DEBUG)


def read_logs() -> str:
    """
    Возвращает содержимое лог-файла как строку.
    Если не найден — сообщает об этом.
    """
    if not os.path.exists(LOG_FILE):
        return "Лог-файл не найден."

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Перекодируем в UTF-8, если не получается прочесть
        with open(LOG_FILE, 'rb') as old_f:
            data = old_f.read()
        converted = data.decode('cp1251', errors='replace')
        with open(LOG_FILE, 'w', encoding='utf-8') as new_f:
            new_f.write(converted)

        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return f.read()

