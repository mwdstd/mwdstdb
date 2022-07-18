from typing import List
from fastapi import APIRouter, Depends, HTTPException

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps.units import convert_out


app = APIRouter(
	dependencies=[
        Depends(get_current_user)
        ]
)

oilfield_out = convert_out(List[models.OilfieldDB])

@app.get("/fields/", 
    tags=["fields"],
    summary="Get list of oilfields",
    dependencies=[]
)
async def get_fields(
        db = Depends(DBEngine.get_db), 
        conv = Depends(oilfield_out), 
        current_user: models.User = Depends(get_current_user)
        ):
    if current_user.role == models.Role.SU:
        query = {}
    elif current_user.role == models.Role.DE:
        query = {'_id': {'$in': current_user.oilfields}}
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    f = await crud.get_all_objects(db, models.Oilfield, query)
    return conv(f)


well_out = convert_out(List[models.WellInfo])

@app.get("/wells/", 
    tags=["wells"],
    summary="Get well information",
    dependencies=[]
)
async def get_well(
        db = Depends(DBEngine.get_db), 
        conv = Depends(well_out), 
        current_user: models.User = Depends(get_current_user)
        ):
    if current_user.role == models.Role.SU:
        flt = {}
    elif current_user.role == models.Role.DE:
        flt = {'field._id': {'$in': current_user.oilfields}}
    else:
        flt = {'_id': current_user.well}

    f = await crud.get_all_wells(db, flt)
    return conv(f)
