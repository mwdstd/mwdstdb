from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models
from .common import delete_object, delete_object, get_child_objects
from .pad import cdelete_pad


async def get_oilfield(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'pads', 
            'let': {'parent_id': '$_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
                {'$sort': {'_id': 1}}
            ], 
            'as': 'pads'
        }},
        {'$lookup': {'from': 'clients', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}},
        ]
    return (await db[models.Oilfield._coll].aggregate(pipeline, **kwargs).to_list(1))[0]

async def cdelete_oilfield(db: AsyncIOMotorDatabase, id, **kwargs):
    children = await get_child_objects(db, models.Pad, id, **kwargs)
    for child in children:
        await cdelete_pad(db, child['_id'], **kwargs)
    await delete_object(db, models.Oilfield, id, **kwargs)
