from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb.models import Survey


async def get_survey(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {'from': 'runs', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'run'}},
        {'$unwind': {'path': '$run'}},
        {'$lookup': {'from': 'boreholes', 'localField': 'run.parent_id', 'foreignField': '_id', 'as': 'borehole'}},
        {'$unwind': {'path': '$borehole'}},
        {'$lookup': {'from': 'wells', 'localField': 'borehole.parent_id', 'foreignField': '_id', 'as': 'well'}},
        {'$unwind': {'path': '$well'}},
        {'$lookup': {'from': 'pads', 'localField': 'well.parent_id', 'foreignField': '_id', 'as': 'pad'}},
        {'$unwind': {'path': '$pad'}},
        {'$lookup': {'from': 'oilfields', 'localField': 'pad.parent_id', 'foreignField': '_id', 'as': 'field'}},
        {'$unwind': {'path': '$field'}},
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}}
    ]
    return (await db[Survey._coll].aggregate(pipeline, **kwargs).to_list(1))[0]