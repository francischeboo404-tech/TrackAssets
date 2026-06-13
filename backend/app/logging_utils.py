import logging
import os
from logging.handlers import RotatingFileHandler
from flask import request, has_request_context


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


def configure_logging(app):
    """Configure production logging with rotating files"""
    if app.debug or app.testing:
        return

    if not os.path.exists("logs"):
        os.mkdir("logs")

    # File handler for all logs
    file_handler = RotatingFileHandler(
        "logs/trackit.log", maxBytes=10485760, backupCount=10  # 10MB
    )

    file_handler.setFormatter(
        RequestFormatter(
            "[%(asctime)s] %(remote_addr)s requested %(url)s\n"
            "%(levelname)s in %(module)s: %(message)s"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # Error-specific file handler
    error_handler = RotatingFileHandler(
        "logs/errors.log", maxBytes=10485760, backupCount=20
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    app.logger.addHandler(error_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("TrackIT Management System startup")
