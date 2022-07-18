from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models
from .common import delete_object, delete_object, get_child_objects
from .borehole import cdelete_borehole


async def get_well(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'boreholes', 
            'let': {'parent_id': '$_id', 'act_id': '$borehole_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$parent_id', '$$parent_id']}}}, 
                {'$set': {'active': {'$eq': ['$_id', '$$act_id']}}},
                {'$sort': {'_id': 1}}
            ], 
            'as': 'boreholes'}
        },
        # {'$set': {'boreholes': {'$concatArrays': [
        #     {'$slice': [ '$boreholes',{ '$subtract': [{ '$size': '$boreholes' }, 1] }]},
        #     [{'$mergeObjects': [{'$arrayElemAt': [ '$boreholes', -1]}, {'active': true}]}]
        # ]}}},
        {'$lookup': {'from': 'pads', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'pad'}},
        {'$unwind': {'path': '$pad'}},
        {'$lookup': {'from': 'oilfields', 'localField': 'pad.parent_id', 'foreignField': '_id', 'as': 'field'}},
        {'$unwind': {'path': '$field'}},
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}},
        {'$lookup': {'from': 'users', 'localField': '_id', 'foreignField': 'well', 'as': 'fes'}},
        ]
    return (await db[models.Well._coll].aggregate(pipeline, **kwargs).to_list(1))[0]


async def get_all_wells(db: AsyncIOMotorDatabase, query: dict = {}, **kwargs):
    pipeline = [
        {'$lookup': {'from': 'pads', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'pad'}},
        {'$unwind': {'path': '$pad'}},
        {'$lookup': {'from': 'oilfields', 'localField': 'pad.parent_id', 'foreignField': '_id', 'as': 'field'}},
        {'$unwind': {'path': '$field'}},
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}},
        {'$match' : query},
        ]
    return (await db[models.Well._coll].aggregate(pipeline, **kwargs).to_list(None))

async def cdelete_well(db: AsyncIOMotorDatabase, id, **kwargs):
    children = await get_child_objects(db, models.Borehole, id, **kwargs)
    for child in children:
        await cdelete_borehole(db, child['_id'], **kwargs)
    await delete_object(db, models.Well, id, **kwargs)
