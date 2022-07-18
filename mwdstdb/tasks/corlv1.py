from typing import List, Optional

from pydantic import BaseModel, validator
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId

from mwdstdb.models import Survey, Station, Interval, Reference
from mwdstdb.models.units import Length, StorageUnitSystem, CalculationUnitSystem
from mwdstdb.utils import convert_units

class Run(BaseModel):
    surveys: List[Survey]
    reference: List[Reference]
    interference_intervals: Optional[List[Interval]]
    casing_depth: Optional[Length]
    dni_rigid: bool = True   
    correction: Optional[dict]
    status_auto: bool = True
    status_msa: bool = True
    status_multi: bool = False
    @validator("interference_intervals", pre=True, always=True)
    def set_ii(cls, v):
        return v or []

class Params(BaseModel):
    runs: List[Run]
    geomag: str
    head_ref: Reference
    plan: Optional[List[Station]] = None

async def correction_lv1(db: AsyncIOMotorDatabase, borehole_id: str, filter_visibility: bool = True):
    pipeline = [
        {'$match' : { '_id' : ObjectId(borehole_id)}},
        {'$lookup': {'from': 'wells', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'well'}},
        {'$unwind': {'path': '$well'}},
        {'$lookup': {'from': 'runs', 
            'let': {'borehole_id': '$_id', 'kick_off': '$kick_off'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$parent_id', '$$borehole_id']}}}, 
                {'$lookup': {
                    'from': 'corrections', 
                    'let': {
                        'rid': '$_id', 
                        'etag': '$etag'
                    }, 
                    'pipeline': [
                        {'$match': {'$expr': {'$and': [{'$eq': ['$$rid', '$parent_id']}, {'$eq': ['$$etag', '$etag']}]}}}, 
                    ], 
                    'as': 'correction'
                }},
                {'$unwind': {'path': '$correction', 'preserveNullAndEmptyArrays': True}},
                {'$set': {
                    'correction_id': '$correction._id', 
                    'correction': '$correction.result_raw', 
                    'casing_depth': {'$max': '$geometry.casing_stop'},
                    'bha.tf_correction': {'$sum': ['$bha.tf_correction', '$tool.tf_correction']}
                }},
                {'$lookup': {
                    'from': 'surveys', 
                    'let': {'parent_id': '$_id'}, 
                    'pipeline': [
                        {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
                        {'$sort': {'_id': 1}}
                    ], 
                    'as': 'surveys'
                }},
                {'$sort': {'_id': 1}},
            ],
        'as': 'runs'}},
        {'$set': {
            'runs.interference_intervals': '$interference_intervals',
            'last_run': {'$last': '$runs'}
        }},
        {'$lookup': {'from': 'plans', 'localField': 'last_run._id', 'foreignField': 'parent_id', 'as': 'plan'}},
        {'$set': {'plan': {'$last': '$plan'}}},
        {'$project' : {
            'runs._id': 1,
            'runs.surveys': 1, 'runs.reference': 1, 'runs.interference_intervals': 1, 
            'runs.correction': 1, 'runs.casing_depth': 1, 'runs.correction_id': 1,
            'runs.status_msa': 1, 'runs.status_auto': 1, 'runs.status_multi': 1,
            'geomag': '$well.geomag', 'plan': '$plan.stations',
            'head_ref': {'$mergeObjects': [
                {'$cond': [{'$isArray': '$ref_traj'}, {'$first': '$ref_traj'}, '$ref_head']},
                {'g': '$well.grav_value', 'grid': '$well.grid_value'}
            ]}
        }}
    ]
    obj = (await db['boreholes'].aggregate(pipeline).to_list(1))[0]
    cids = [r.get('correction_id') for r in obj['runs']]
    rids = [r.get('_id') for r in obj['runs']]

    res = convert_units(Params, obj, StorageUnitSystem, CalculationUnitSystem)

    if filter_visibility:
        for r in res['runs']:
            r['reference'] = [r for r, s in zip(r['reference'], r['surveys']) if s['visible']]
            r['surveys'] = [s for s in r['surveys'] if s['visible']]

    return res, cids, rids