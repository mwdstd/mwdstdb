from os import environ
from motor.motor_asyncio import AsyncIOMotorClient
from bson.codec_options import CodecOptions

MONGO_DB_URL = environ.get("MONGO_DB_URL")
MONGO_DB_NAME = environ.get("MONGO_DB_NAME")
options = CodecOptions(tz_aware=True)

class DBEngine:
    __client : AsyncIOMotorClient = None

    @classmethod
    def start(cls):
        cls.__client = AsyncIOMotorClient(str(MONGO_DB_URL))

    @classmethod
    def stop(cls):
        cls.__client.close()

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        return cls.__client

    @classmethod
    def get_db(cls):
        return cls.__client.get_database(name=MONGO_DB_NAME, codec_options=options)

