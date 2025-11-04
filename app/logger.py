import os
import logging

logging.basicConfig(
    format="%(filename)s - %(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
if os.environ.get("ENV") == "production":
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.getLogger().setLevel(logging.DEBUG)


def get_logger(filename: str) -> logging.Logger:
    return logging.getLogger(filename)