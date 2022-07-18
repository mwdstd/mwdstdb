from typing import Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
import pymongo

async def create_object(db: AsyncIOMotorDatabase, objType, obj: dict, **kwargs):
    res = await db[objType._coll].insert_one(obj, **kwargs)
    return str(res.inserted_id)

async def create_child_object(db: AsyncIOMotorDatabase, objType, parent_id: str, obj: dict, **kwargs):
    res = await db[objType._coll].insert_one({'parent_id': ObjectId(parent_id), **obj}, **kwargs)
    return str(res.inserted_id)

async def update_object(db: AsyncIOMotorDatabase, objType, id: str, obj: dict, **kwargs):
    res = await db[objType._coll].update_one({'_id': ObjectId(id)}, {'$set': obj}, **kwargs)
    if res.matched_count == 0:
        raise KeyError()

async def add_array_element(db: AsyncIOMotorDatabase, objType, id: str, fieldName: str, value: List[Any], **kwargs):
    await db[objType._coll].update_one({'_id': ObjectId(id)}, { '$push': { fieldName: { '$each': value} } }, **kwargs)

async def add_to_set(db: AsyncIOMotorDatabase, objType, id: str, fieldName: str, value: List[Any], **kwargs):
    await db[objType._coll].update_one({'_id': ObjectId(id)}, { '$addToSet': { fieldName: { '$each': value} } }, **kwargs)

async def remove_array_element(db: AsyncIOMotorDatabase, objType, id: str, fieldName: str, value: Any, **kwargs):
    await db[objType._coll].update_one({'_id': ObjectId(id)}, { '$pull': { fieldName: value } }, **kwargs)

async def delete_object_fields(db: AsyncIOMotorDatabase, objType, id: str, fields, **kwargs):
    await db[objType._coll].update_one({'_id': ObjectId(id)}, {'$unset': {f: '' for f in fields}}, **kwargs)

async def delete_object(db: AsyncIOMotorDatabase, objType, id: str, **kwargs):
    res = await db[objType._coll].delete_one({'_id': ObjectId(id)}, **kwargs)
    if res.deleted_count == 0:
        raise KeyError()

async def delete_child_objects(db: AsyncIOMotorDatabase, childType, parent_id: str, **kwargs):
    return await db[childType._coll].delete_many({'parent_id': ObjectId(parent_id)}, **kwargs)

async def get_object(db: AsyncIOMotorDatabase, objType, id: str, **kwargs):
    o = await db[objType._coll].find_one({'_id': ObjectId(id)}, **kwargs)
    if o is None:
        raise KeyError()
    return o

async def find_object(db: AsyncIOMotorDatabase, objType, query: dict, **kwargs):
    return await db[objType._coll].find_one(query, **kwargs)

async def find_and_update_object(db: AsyncIOMotorDatabase, objType, query: dict, obj: dict, **kwargs):
    return await db[objType._coll].update_one(query, {'$set': obj}, **kwargs)

async def find_and_delete_object(db: AsyncIOMotorDatabase, objType, query: dict, **kwargs):
    return await db[objType._coll].delete_one(query, **kwargs)

async def get_object_field(db: AsyncIOMotorDatabase, objType, id: str, fieldName: str, **kwargs):
    obj: dict = await db[objType._coll].find_one({'_id': ObjectId(id)}, {'_id': False, fieldName: True }, **kwargs)
    if obj is None:
        raise KeyError()
    return obj.get(fieldName)

async def get_all_objects(db: AsyncIOMotorDatabase, objType, query:dict = None, skip: int = 0, limit: int = 100, **kwargs):
    return await db[objType._coll].find(query, **kwargs).sort([('_id', pymongo.ASCENDING)]).skip(skip).limit(limit).to_list(None)

async def get_child_objects(db: AsyncIOMotorDatabase, childType, parent_id: str, skip: int = 0, limit: int = 100, sort: list = [('_id', pymongo.ASCENDING)], **kwargs):
    return await db[childType._coll].find({'parent_id': ObjectId(parent_id)}, **kwargs).sort(sort).skip(skip).limit(limit).to_list(None)

async def has_children(db: AsyncIOMotorDatabase, childType, parent_id: str, **kwargs):
    return (await db[childType._coll].count_documents({'parent_id': ObjectId(parent_id)}, **kwargs)) > 0