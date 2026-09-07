"""Shared MongoDB connection for the application process."""
from functools import lru_cache
import logging
import os

from pymongo import MongoClient

logger = logging.getLogger('uvicorn.error')


@lru_cache(maxsize=1)
def client():
    return MongoClient(
        os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017'),
        serverSelectionTimeoutMS=3000,
        appname='pesc-mate-backend',
    )


def database():
    return client()[os.environ.get('MONGODB_DATABASE', 'pesc_mate')]


def log_crud(operation, collection, detail=None):
    """Log database actions without document contents or credentials."""
    suffix = f' | {detail}' if detail else ''
    logger.info('DB CRUD | %s | %s%s', operation, collection, suffix)
