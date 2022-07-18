from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models


run_export_pipeline = [
    {'$lookup': {
        'from': 'surveys', 
        'let': {'parent_id': '$_id'}, 
        'pipeline': [
            {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
            {'$sort': {'_id': 1}}
        ], 
        'as': 'surveys'
    }},
    {'$lookup': {'from': 'ci', 'localField': 'ci_id', 'foreignField': '_id', 'as': 'ci'}}, 
    {'$unwind': {'path': '$ci', 'preserveNullAndEmptyArrays': True}}, 
    {'$set': {'ci': '$ci.stations'}},
    {'$lookup': {'from': 'plans', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'plan'}},
    {'$set': {'plan': {'$last': '$plan'}}},
]

borehole_export_pipeline = [
    {'$lookup': {
        'from': 'runs', 
        'let': {'borehole_id': '$_id'}, 
        'pipeline': [
            {'$match': {'$expr': {'$eq': ['$parent_id', '$$borehole_id']}}}, 
            {'$sort': {'_id': 1}}, 
            *run_export_pipeline
        ], 
        'as': 'runs'}
    }
]

async def export_well(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'boreholes', 
            'let': {'well_id': '$_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$parent_id', '$$well_id']}}}, 
                {'$sort': {'_id': 1}},
                *borehole_export_pipeline
            ],
            'as': 'boreholes'}
        }
    ]
    return (await db[models.Well._coll].aggregate(pipeline, **kwargs).to_list(1))[0]

async def export_borehole(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        *borehole_export_pipeline
    ]
    return (await db[models.Borehole._coll].aggregate(pipeline, **kwargs).to_list(1))[0]

async def export_run(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        *run_export_pipeline
    ]
    return (await db[models.Run._coll].aggregate(pipeline, **kwargs).to_list(1))[0]
