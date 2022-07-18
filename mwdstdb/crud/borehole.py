from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from mwdstdb import models
from .common import delete_object, delete_object, delete_child_objects, get_child_objects
from .run import cdelete_run


async def get_borehole(db: AsyncIOMotorDatabase, id: str, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {
            'from': 'runs', 
            'let': {'parent_id': '$_id', 'act_id': '$run_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$parent_id', '$$parent_id']}}}, 
                {'$set': {'active': {'$eq': ['$_id', '$$act_id']}}},
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
                {'$lookup': {'from': 'plans', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'plan'}},
                {'$set': {'plan': {'$last': '$plan'}}},
                {'$sort': {'_id': 1}}
            ], 
            'as': 'runs'}
        },
        {'$lookup': {'from': 'tasks', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'tasks'}},
        # {'$set': {'tasks': {"$arrayToObject": {
        #     "$map": {
        #         "input": "$tasks",
        #         "as": "el",
        #         "in": {"k": "$$el.type", "v": "$$el"}
        #         }
        #     }}}},
        {'$lookup': {'from': 'wells', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'well'}},
        {'$unwind': {'path': '$well'}},
        {'$lookup': {'from': 'pads', 'localField': 'well.parent_id', 'foreignField': '_id', 'as': 'pad'}},
        {'$unwind': {'path': '$pad'}},
        {'$lookup': {'from': 'oilfields', 'localField': 'pad.parent_id', 'foreignField': '_id', 'as': 'field'}},
        {'$unwind': {'path': '$field'}},
        {'$lookup': {'from': 'clients', 'localField': 'field.parent_id', 'foreignField': '_id', 'as': 'client'}},
        {'$unwind': {'path': '$client'}},
        {'$set': {
            'active': {'$eq': ['$_id', '$well.borehole_id']},
            'geometry_finished' : { '$ifNull': [{'$last': '$runs.geometry'}, '$geometry']},
            'last_plan': {'$last': '$runs.plan'}
        }}
        ]
    return (await db[models.Borehole._coll].aggregate(pipeline, **kwargs).to_list(1))[0]

async def cdelete_borehole(db: AsyncIOMotorDatabase, id, **kwargs):
    children = await get_child_objects(db, models.Run, id, **kwargs)
    for child in children:
        await cdelete_run(db, child['_id'], **kwargs)
    await delete_child_objects(db, models.Task, id, **kwargs)
    await delete_object(db, models.Borehole, id, **kwargs)

async def get_borehole_last_depth(db: AsyncIOMotorDatabase, id, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(id)}},
        {'$lookup': {'from': 'runs', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'runs'}},
        {'$project': {
            'last' : {'$max': {'$reduce': {
                'input': '$runs.slidesheet.md_stop',
                        'initialValue': [],
                        'in': {'$concatArrays': ['$$value', '$$this']}
            }}},
            }
        }
    ]
    return (await db[models.Borehole._coll].aggregate(pipeline, **kwargs).to_list(1))[0]['last']
