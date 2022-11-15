from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import ValidationError

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.models.validation import validate_borehole
from .core import ensure_manual_mode, calc_well, calc_borehole, create_borehole as create_borehole_impl
from .deps.auth import get_current_user
from .deps.units import convert_out, well_in_update, borehole_in_create
from .deps.actrl import Action, Authorize
from .deps import exists


app = APIRouter(
	dependencies=[
        Depends(get_current_user),
        Depends(exists.well)
        ]
)

well_out = convert_out(models.WellGet)

@app.get("/{well_id}", 
    tags=["wells"],
    summary="Get well information",
#    response_model=models.WellGet,
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.well_read))]
)
async def get_well(
        well_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(well_out), 
        ):
    w = await crud.get_well(db, well_id)
    return conv(w)


@app.put("/{well_id}", 
    tags=["wells"],
    summary="Update well information",
    dependencies=[Depends(Authorize(Action.well_write))]
)
async def update_well(
        well_id: str, 
        d: dict = Depends(well_in_update), 
        db = Depends(DBEngine.get_db), 
        ):
    # if await crud.has_children(db, models.Borehole, well_id):
    #     old_geomag = await crud.get_object_field(db, models.Well, well_id, 'geomag')
    #     if d['geomag'] != old_geomag:
    #         raise HTTPException(status_code=403, detail='Can not change geomag model if a child borehole exists')
    await crud.update_object(db, models.Well, well_id, d)
    await calc_well(db, well_id)

@app.put("/{well_id}/maintenance", 
    tags=["wells"],
    summary="Set well maintenace mode",
    dependencies=[Depends(Authorize(Action.well_maintenance))]
)
async def set_maintenance(
        well_id: str, 
        value: bool = Body(...), 
        db = Depends(DBEngine.get_db), 
        ):
    await crud.update_object(db, models.Well, well_id, {'maintenance_mode': value})

@app.delete("/{well_id}", 
    tags=["wells"],
    summary="Delete well",
    dependencies=[Depends(Authorize(Action.well_delete))]
)
async def delete_well(
        well_id: str, 
        db = Depends(DBEngine.get_db), 
        ):
    # if await crud.has_children(db, models.Borehole, well_id):
    #     # check for permissions
    #     raise HTTPException(status_code=403, detail="Cascade delete is not authorized")

    await crud.cdelete_well(db, well_id)

@app.post("/{well_id}/boreholes", 
    tags=["boreholes"],
    summary="Create new borehole",
    status_code=201,
    dependencies=[Depends(Authorize(Action.borehole_create))]
)
async def create_borehole_manual(
		well_id: str, 
		response: Response, d: 
		dict = Depends(borehole_in_create), 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
        ):
    await ensure_manual_mode(db, well_id)

    # check there is no active borehole
    if await crud.get_object_field(db, models.Well, well_id, 'borehole_id') is not None:
        raise HTTPException(status_code=403, detail="Well has an active borehole")

    # check for ref validity
    geomag = await crud.get_object_field(db, models.Well, well_id, 'geomag')
    try:
        models.Borehole.validate_ref(d, geomag)
    except ValidationError as err:
        raise HTTPException(422, detail=err.errors())

    async with await dbc.start_session() as s:
        async with s.start_transaction():
            borehole_id = await create_borehole_impl(db, well_id, d, session=s)
            try:
                await validate_borehole(db, borehole_id, session=s)
            except ValidationError as err:
                raise HTTPException(422, detail=err.errors())

    await calc_borehole(db, str(borehole_id))

    response.headers["Location"] = f'/boreholes/{borehole_id}'
    return borehole_id
