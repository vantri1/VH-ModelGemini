# utils/logger.py
import logging

def setup_logger() -> logging.Logger:
    """
    Hàm này cấu hình một logger duy nhất để sử dụng trong toàn bộ script.
    Việc này giúp quản lý log một cách tập trung và nhất quán.
    """
    logger = logging.getLogger("TranslatorLogger")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger