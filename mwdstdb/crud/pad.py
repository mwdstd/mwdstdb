from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models
from .common import delete_object, delete_object, get_child_objects
from .well import cdelete_well


async def get_pad(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'wells', 
            'let': {'parent_id': '$_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
                {'$sort': {'_id': 1}}
            ], 
            'as': 'wells'
        }},
        {'$lookup': {'from': 'oilfields', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'field'}},
        {'$unwind': {'path': '$field'}},
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}},
        ]
    return (await db[models.Pad._coll].aggregate(pipeline, **kwargs).to_list(1))[0]

async def cdelete_pad(db: AsyncIOMotorDatabase, id, **kwargs):
    children = await get_child_objects(db, models.Well, id, **kwargs)
    for child in children:
        await cdelete_well(db, child['_id'], **kwargs)
    await delete_object(db, models.Pad, id, **kwargs)
