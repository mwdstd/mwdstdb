from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models
from .common import delete_object, delete_object, get_child_objects
from .oilfield import cdelete_oilfield

async def get_client(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'oilfields', 
            'let': {'parent_id': '$_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
                {'$sort': {'_id': 1}}
            ], 
            'as': 'oilfields'
        }},
    ]
    return (await db[models.Client._coll].aggregate(pipeline, **kwargs).to_list(1))[0]

async def cdelete_client(db: AsyncIOMotorDatabase, id, **kwargs):
    children = await get_child_objects(db, models.Oilfield, id, **kwargs)
    for child in children:
        await cdelete_oilfield(db, child['_id'], **kwargs)
    await delete_object(db, models.Client, id, **kwargs)
