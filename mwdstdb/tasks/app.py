from typing import Optional
from os import environ
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from celery.utils.log import get_task_logger

from mwdstdb.database import DBEngine
from mwdstdb import rpc

redis_url = environ.get("REDIS_URL")

capp = Celery('tasks', broker=redis_url)
logger = get_task_logger(__name__)


@worker_ready.connect
def db_connect(**kwargs):
    DBEngine.start()
    rpc.start()

@worker_shutdown.connect
#async def db_shutdown(**kwargs):
def db_shutdown(**kwargs):
    #await client.aclose()
    DBEngine.stop()
