from motor.motor_asyncio import AsyncIOMotorDatabase
from mwdstdb.models import Well


async def get_active_runs(db: AsyncIOMotorDatabase, query = {}, **kwargs):
    pipeline = [
        {'$replaceRoot': {'newRoot': {'well': '$$ROOT'}}},
        {'$lookup': {'from': 'pads', 'localField': 'well.parent_id', 'foreignField': '_id', 'as': 'pad'}},
        {'$unwind': {'path': '$pad'}}, 
        {'$lookup': {'from': 'oilfields', 'localField': 'pad.parent_id', 'foreignField': '_id', 'as': 'field'}}, 
        {'$unwind': {'path': '$field'}}, 
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}}, 
        {'$unwind': {'path': '$client'}}, 
        {'$lookup': {'from': 'boreholes', 'localField': 'well.borehole_id', 'foreignField': '_id', 'as': 'borehole'}}, 
        {'$unwind': {'path': '$borehole'}}, 
        {'$lookup': {'from': 'runs', 'localField': 'borehole.run_id', 'foreignField': '_id', 'as': 'run'}}, 
        {'$unwind': {'path': '$run'}}, 
        {'$lookup': {'from': 'plans', 'localField': 'run._id', 'foreignField': 'parent_id', 'as': 'plan'}},
        {'$set': {'plan': {'$last': '$plan'}}},
        {'$set': {'plan.length': { '$size': "$plan.stations" }}},
        {'$lookup': {
            'from': 'corrections', 
            'let': {'pid': '$run._id', 'etag': '$run.etag'}, 
            'pipeline': [
                {'$match': {'$expr': {'$and': [{'$eq': ['$$pid', '$parent_id']}, {'$eq': ['$$etag', '$etag']}]}}}
            ], 
            'as': 'correction'
            }
        }, 
        {'$unwind': {'path': '$correction', 'preserveNullAndEmptyArrays': True}},
        {'$match' : query},
    ]
    return (await db[Well._coll].aggregate(pipeline, **kwargs).to_list(None))