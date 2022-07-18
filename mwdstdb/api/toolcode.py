from typing import List
from fastapi import APIRouter, Depends, Response

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps import exists


app = APIRouter(
	dependencies=[Depends(get_current_user)]
)

@app.get("/", 
    tags=["toolcodes"],
    summary="Get toolcodes",
    response_model=List[models.ToolcodeInfo],
    response_model_by_alias=False
)
async def get_toolcodes(
        db = Depends(DBEngine.get_db), 
        ):
	r = await crud.get_all_objects(db, models.ToolcodeInfo)
	return r

@app.post("/", 
    tags=["toolcodes"],
    summary="Create new toolcode",
    status_code=201,
)
async def create_toolcode(
        response: Response, 
        tc: models.Toolcode, 
        db = Depends(DBEngine.get_db), 
        ):
	id = await crud.create_object(db, models.Toolcode, tc.dict())
	response.headers["toolcodes"] = f'/toolcodes/{tc.name}'
	return id

@app.get("/{name}", 
    tags=["toolcodes"],
    summary="Get toolcode",
    response_model=models.Toolcode,
    response_model_by_alias=False
)
async def get_toolcode(
        name: str, 
        db = Depends(DBEngine.get_db), 
        ):
    r = await crud.find_object(db, models.Toolcode, {'name': name})
    if r is None:
        raise exists.not_found
    return r

@app.put("/{name}", 
    tags=["toolcodes"],
    summary="Update toolcode"
)
async def update_toolcode(
        name: str, 
        tc: models.Toolcode, 
        db = Depends(DBEngine.get_db), 
        ):
    tc.name = name
    res = await crud.find_and_update_object(db, models.Toolcode, {'name': name}, tc.dict())
    if res.matched_count == 0:
        raise exists.not_found

@app.delete("/{name}", 
    tags=["toolcodes"],
    summary="Delete toolcode"
)
async def delete_toolcode(
        name: str, 
        db = Depends(DBEngine.get_db), 
        ):
    res = await crud.find_and_delete_object(db, models.Toolcode, {'name': name})
    if res.deleted_count == 0:
        raise exists.not_found

