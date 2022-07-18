from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models
from .common import delete_object, delete_object, delete_child_objects, get_object_field


async def get_run(db: AsyncIOMotorDatabase, id: str, filter_visibility: bool = True, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'surveys', 
            'let': {'parent_id': '$_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
                {'$sort': {'_id': 1}}
            ], 
            'as': 'surveys'
        }},
        {'$lookup': {'from': 'boreholes', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'borehole'}},
        {'$unwind': {'path': '$borehole'}},
        {'$lookup': {'from': 'wells', 'localField': 'borehole.parent_id', 'foreignField': '_id', 'as': 'well'}},
        {'$unwind': {'path': '$well'}},
        {'$lookup': {'from': 'pads', 'localField': 'well.parent_id', 'foreignField': '_id', 'as': 'pad'}},
        {'$unwind': {'path': '$pad'}},
        {'$lookup': {'from': 'oilfields', 'localField': 'pad.parent_id', 'foreignField': '_id', 'as': 'field'}},
        {'$unwind': {'path': '$field'}},
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}},
        {'$set': {'active': {'$eq': ['$_id', '$borehole.run_id']}}},
        {'$set': {'borehole.active': {'$eq': ['$borehole._id', '$well.borehole_id']}}},
        {'$lookup': {
            'from': 'corrections', 
            'let': {
                'pid': '$_id', 
                'etag': '$etag'
            }, 
            'pipeline': [
                {'$match': {'$expr': {'$and': [{'$eq': ['$$pid', '$parent_id']}, {'$eq': ['$$etag', '$etag']}]}}}, 
            ], 
            'as': 'correction'
        }},
        {'$unwind': {'path': '$correction', 'preserveNullAndEmptyArrays': True}},
        {'$lookup': {'from': 'tasks', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'tasks'}},
        {'$lookup': {'from': 'ci', 'localField': 'ci_id', 'foreignField': '_id', 'as': 'ci'}}, 
        {'$unwind': {'path': '$ci', 'preserveNullAndEmptyArrays': True}}, 
        {'$set': {'ci': '$ci.stations'}},
        {'$lookup': {'from': 'plans', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'plan'}},
        {'$set': {'plan': {'$last': '$plan'}}},
    ]
    run = (await db[models.Run._coll].aggregate(pipeline, **kwargs).to_list(1))[0]
    if filter_visibility:
        if 'stations' in run:
            run['stations'] = [r for r, s in zip(run['stations'], run['surveys']) if s['visible']]
            run['reference'] = [r for r, s in zip(run['reference'], run['surveys']) if s['visible']]
        run['surveys'] = [s for s in run['surveys'] if s['visible']]
    return run

async def cdelete_run(db: AsyncIOMotorDatabase, id, **kwargs):
    ci_id = await get_object_field(db, models.Run, id, "ci_id", **kwargs)
    if ci_id is not None:
        await delete_object(db, models.ContinuousInclination, ci_id, **kwargs)
    await delete_child_objects(db, models.Plan, id, **kwargs)
    await delete_child_objects(db, models.CorrectionGet, id, **kwargs)
    await delete_child_objects(db, models.Task, id, **kwargs)
    await delete_child_objects(db, models.Survey, id, **kwargs)
    await delete_object(db, models.Run, id, **kwargs)
