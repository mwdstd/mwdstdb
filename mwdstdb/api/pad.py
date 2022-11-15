from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import ValidationError

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.models.validation import validate_borehole
from .core import calc_well, create_borehole
from .deps.auth import get_current_user
from .deps.units import pad_in, well_in_create, convert_out
from .deps.actrl import Action, Authorize
from .deps import exists


app = APIRouter(
	dependencies=[
        Depends(get_current_user),
        Depends(exists.pad)
        ]
)

pad_out = convert_out(models.PadGet)


@app.get("/{pad_id}", 
    tags=["pads"],
    summary="Get pad information",
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.pad_read))]
)
async def get_pad(
        pad_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(pad_out), 
        ):
    pad = await crud.get_pad(db, pad_id)
    return conv(pad)

@app.put("/{pad_id}", 
    tags=["pads"],
    summary="Update pad information",
    dependencies=[Depends(Authorize(Action.pad_write))]
)
async def update_pad(
        pad_id: str, 
        d: dict = Depends(pad_in), 
        db = Depends(DBEngine.get_db), 
        ):
    await crud.update_object(db, models.Pad, pad_id, d)

@app.delete("/{pad_id}", 
    tags=["pads"],
    summary="Delete pad",
    dependencies=[Depends(Authorize(Action.pad_delete))]
)
async def delete_pad(
        pad_id: str, 
        db = Depends(DBEngine.get_db), 
        ):
    if await crud.has_children(db, models.Well, pad_id):
        # check for permissions
        raise HTTPException(status_code=403, detail="Cascade delete is not authorized")

    await crud.cdelete_pad(db, pad_id)

@app.post("/{pad_id}/wells", 
    tags=["wells"],
    summary="Add new well to pad",
    status_code=201,
    dependencies=[Depends(Authorize(Action.well_create))]
)
async def create_well(
        pad_id: str, 
        response: Response, 
        d: dict = Depends(well_in_create), 
        db = Depends(DBEngine.get_db), 
        dbc = Depends(DBEngine.get_client), 
        ):

    boreholes = d.get('boreholes') or []
    del d['boreholes']

    for b in boreholes:
        geomag = d['geomag']
        try:
            models.Borehole.validate_ref(b, geomag)
        except ValidationError as err:
            raise HTTPException(422, detail=err.errors())

    async with await dbc.start_session() as s:
        async with s.start_transaction():
            well_id = await crud.create_child_object(db, models.Well, pad_id, d, session=s)
            try:
                for b in boreholes:
                    borehole_id = await create_borehole(db, well_id, b, session=s)
                    await validate_borehole(db, borehole_id, session=s)
            except ValidationError as err:
                raise HTTPException(422, detail=err.errors())


    await calc_well(db, str(well_id))

    response.headers["Location"] = f'/wells/{well_id}'
    return well_id