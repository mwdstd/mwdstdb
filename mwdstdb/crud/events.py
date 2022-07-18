import asyncio
from typing import List
from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId

from mwdstdb import models


THROTTLING_DELAY = 3 # sec

async def global_event_generator(request: Request, db: AsyncIOMotorDatabase):
    colls = [
        models.Client._coll,
        models.Oilfield._coll,
        models.Pad._coll,
        models.Well._coll,
        models.Borehole._coll,
    ]
    
    pipeline = [
        {
            '$match': {
                '$or': [
                    *[{'ns.coll': c} for c in colls], 
                    {'ns.coll': models.Run._coll, 'operationType': 'insert'},
                    {'ns.coll': models.Run._coll, 'operationType': 'delete'},
                ]
            }
        }
    ]
    async with db.watch(pipeline) as stream:
        while True:
            if await request.is_disconnected():
                break

            change = await stream.try_next()

            if change is None:
                await asyncio.sleep(THROTTLING_DELAY)
                continue
            
            evt = None

            while change is not None:
                op_type = change['operationType']
                if op_type in ['insert', 'replace', 'update', 'delete']:
                    evt = {
                        "event": "update",
                        "data": ""
                    }
                change = await stream.try_next()

            if evt is not None:
                yield evt

# WARN: full collection lookup may skip events
async def object_event_generator(objType, request: Request, db: AsyncIOMotorDatabase, obj_id: str = None, obj_ids: List[str] = None):
    coll = db[objType._coll]
    pipeline = [
        {'$match': {'documentKey': { '_id' : ObjectId(obj_id)}}}
    ] if obj_id is not None else [
        {'$match': {'$or': [
            {'documentKey': { '_id' : ObjectId(id)}} for id in obj_ids
        ]}}
    ] if obj_id is not None else []
    async with coll.watch(pipeline) as stream:
        while True:
            if await request.is_disconnected():
                break

            change = await stream.try_next()

            if change is None:
                await asyncio.sleep(THROTTLING_DELAY)
                continue
            
            evt = None

            while change is not None:
                op_type = change['operationType']

                if op_type in ['insert', 'replace', 'update']:
                    evt = {
                        "event": "update",
                        "data": str(change['documentKey']['_id'])
                    }
                elif op_type == 'delete':
                    evt = {
                        "event": "delete",
                        "data": str(change['documentKey']['_id'])
                    }
                change = await stream.try_next()

            if evt is not None:
                yield evt

async def task_event_generator(request: Request, db, task_id: str = None):
    pipeline = [{'$match': {'documentKey': { '_id' : ObjectId(task_id)}}}] if task_id is not None else []
    async with db[models.Task._coll].watch(pipeline, full_document='updateLookup') as stream:
        async for change in stream:
            if await request.is_disconnected():
                break

            op_type = change['operationType']

            if op_type in ['insert', 'replace', 'update']:
                cor = change['fullDocument']
                yield {
                    "event": "update",
                    #"data": 'status'
                    "data": models.TaskDb.parse_obj(cor).json()
                }
            elif op_type == 'delete':
                yield {
                    "event": "delete",
                    "data": str(change['documentKey']['_id'])
                }
