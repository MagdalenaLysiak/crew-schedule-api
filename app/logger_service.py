import logging
from typing import Optional


class LoggerService:
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def info(self, message: str, extra: Optional[dict] = None):
        self.logger.info(message, extra=extra)

    def error(self, message: str, extra: Optional[dict] = None):
        self.logger.error(message, extra=extra)

    def warning(self, message: str, extra: Optional[dict] = None):
        self.logger.warning(message, extra=extra)

    def debug(self, message: str, extra: Optional[dict] = None):
        self.logger.debug(message, extra=extra)


def get_logger_service() -> LoggerService:
    return LoggerService()
