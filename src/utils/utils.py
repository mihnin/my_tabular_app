import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_FILE = "logs/app.log"

def setup_logger(debug: bool = False):
    """
    Инициализирует логгер для приложения.
    
    :param debug: Если True, будет установлен уровень DEBUG, иначе INFO.
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger()
    # Удалим все старые хендлеры, чтобы не дублировать логи
    logger.handlers = []

    # Устанавливаем общий уровень логов
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

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

    # Также выводим логи в консоль (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Если хотите включить подробные логи у самой библиотеки AutoGluon
    # logging.getLogger("autogluon").setLevel(logging.DEBUG)

    logger.info("========== Application Started ==========")
    if debug:
        logger.debug("Logger запущен в режиме DEBUG.")

def read_logs() -> str:
    """
    Возвращает содержимое лог-файла как строку.
    Если файл не найден — возвращает текст об отсутствии лог-файла.
    """
    if not os.path.exists(LOG_FILE):
        return "Лог-файл не найден."

    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Если произошла ошибка декодирования, перезапишем в UTF-8
        with open(LOG_FILE, 'rb') as old_f:
            data = old_f.read()
        converted = data.decode('cp1251', errors='replace')
        with open(LOG_FILE, 'w', encoding='utf-8') as new_f:
            new_f.write(converted)

        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return f.read()