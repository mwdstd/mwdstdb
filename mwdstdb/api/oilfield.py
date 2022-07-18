from fastapi import APIRouter, Depends, HTTPException, Response

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps.units import oilfield_in, pad_in, convert_out
from .deps.actrl import Action, Authorize
from .deps import exists


app = APIRouter(
	dependencies=[
        Depends(get_current_user),
        Depends(exists.oilfield)
        ]
)

oilfield_out = convert_out(models.OilfieldGet)


@app.get("/{field_id}", 
    tags=["fields"],
    summary="Get oilfield information",
#    response_model=models.OilfieldGet,
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.oilfield_read))]
)
async def get_field(
        field_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(oilfield_out), 
        ):
    f = await crud.get_oilfield(db, field_id)
    return conv(f)


@app.put("/{field_id}", 
    tags=["fields"],
    summary="Update oilfield information",
    dependencies=[Depends(Authorize(Action.oilfield_write))]
)
async def update_field(
        field_id: str, 
        d: dict = Depends(oilfield_in), 
        db = Depends(DBEngine.get_db), 
        ):
    await crud.update_object(db, models.Oilfield, field_id, d)


@app.delete("/{field_id}", 
    tags=["fields"],
    summary="Delete oilfield",
    dependencies=[Depends(Authorize(Action.oilfield_delete))]
)
async def delete_field(
        field_id: str, 
        db = Depends(DBEngine.get_db), 
        ):
    if await crud.has_children(db, models.Pad, field_id):
        # check for permissions
        raise HTTPException(status_code=403, detail="Cascade delete is not authorized")

    await crud.cdelete_oilfield(db, field_id)

@app.post("/{field_id}/pads", 
    tags=["pads"],
    summary="Add new pad to oilfield",
    status_code=201,
    dependencies=[Depends(Authorize(Action.pad_create))]
)
async def create_pad(
        field_id: str, 
        response: Response, 
        d: dict = Depends(pad_in), 
        db = Depends(DBEngine.get_db), 
        ):
    id = await crud.create_child_object(db, models.Pad, field_id, d)
    response.headers["Location"] = f'/pads/{id}'
    return id

