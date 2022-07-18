from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
import jsons
from hashlib import md5
from mwdstdb import models


async def get_etag_source(db: AsyncIOMotorDatabase, run_id):
    pipeline = [
        {'$match' : { '_id' : ObjectId(run_id)}},
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
        #TODO: is_dni_rigid
        # {'$lookup': {'from': 'plans', 'localField': 'borehole.plan_id', 'foreignField': '_id', 'as': 'plan'}},
        # {'$unwind': {'path': '$plan', 'preserveNullAndEmptyArrays': True }},
        {'$lookup': {'from': 'ci', 'localField': 'ci_id', 'foreignField': '_id', 'as': 'ci'}}, 
        {'$unwind': {'path': '$ci', 'preserveNullAndEmptyArrays': True}}, 
        {'$set': {'ci': '$ci.stations'}},
        {'$project': {
            '_id' : 0,
            'parent_id' : 0,
            'ci_id' : 0,
            'etag' : 0,
            'name' : 0,
            'tool.sn' : 0,
            'tool.name' : 0,
            'tool.dni' : 0,
            'toolcode' : 0,
            'bha.structure.description' : 0,
            'bha.structure.sn' : 0,
            'surveys._id' : 0,
            'surveys.parent_id' : 0,
            'borehole._id' : 0,
            'borehole.parent_id' : 0,
            'borehole.name' : 0,
            'borehole.geometry' : 0,
            'borehole.geometry_finished' : 0,
            'borehole.plan_id' : 0,
            'borehole.original_traj' : 0,
            'borehole.run_id' : 0,
            'well._id' : 0,
            'well.parent_id' : 0,
            'well.name' : 0,
            'well.data_mode' : 0,
            'well.borehole_id' : 0,
            'plan._id' : 0,
            'plan.parent_id' : 0,
            'correction' :  0,
            'reference': 0,
            'head_ref': 0,
            'stations': 0,
            'borehole.links': 0, 
            'borehole.program': 0,
            'borehole.last_depth': 0,
            'borehole.runs_gyro': 0,
            'ci.survey_id': 0,
            'slidesheet.survey_id': 0,
            'plan.survey_id': 0,
            'plan.revision': 0,
            'plan.uploaded': 0,
        }}
    ]
    return (await db[models.Run._coll].aggregate(pipeline).to_list(1))[0]
    
async def compute_etag(db: AsyncIOMotorDatabase, run_id):
    obj = await get_etag_source(db, run_id)
    s = jsons.dumps(obj, {'sort_keys': True})
    return md5(s.encode('utf-8')).hexdigest()
