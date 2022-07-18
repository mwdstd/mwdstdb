from typing import List
from fastapi import APIRouter, HTTPException, Depends, Response, Body
from bson.objectid import ObjectId
from pydantic import ValidationError

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.models.validation import validate_borehole
from .core import ensure_manual_mode, calc_borehole, calc_run, create_run as create_run_impl
from .deps.auth import get_current_user
from .deps.units import convert_out, borehole_in_update, run_in_create
from .deps.actrl import Action, Authorize
from .deps import exists

app = APIRouter(
	dependencies=[
		Depends(get_current_user), 
		Depends(exists.borehole)
	]
)

borehole_out = convert_out(models.BoreholeGet)

@app.get("/{borehole_id}", 
    tags=["boreholes"],
    summary="Get borehole information",
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.borehole_read))]
)
async def get_borehole(
		borehole_id: str, 
		db = Depends(DBEngine.get_db), 
		conv = Depends(borehole_out), 
		):
	b = await crud.get_borehole(db, borehole_id)
	return conv(b)


@app.put("/{borehole_id}", 
    tags=["boreholes"],
    summary="Update borehole information",
    dependencies=[Depends(Authorize(Action.borehole_write))]
)
async def update_borehole(
		borehole_id: str, 
		d: dict = Depends(borehole_in_update), 
		db = Depends(DBEngine.get_db), 
		):
	#check for ref validity
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	geomag = await crud.get_object_field(db, models.Well, well_id, 'geomag')
	try:
		models.Borehole.validate_ref(d, geomag)
	except ValidationError as err:
		raise HTTPException(422, detail=err.errors())

	await crud.update_object(db, models.Borehole, borehole_id, d)
	await calc_borehole(db, borehole_id)


@app.delete("/{borehole_id}", 
    tags=["boreholes"],
    summary="Delete borehole",
    dependencies=[Depends(Authorize(Action.borehole_delete))]
)
async def delete_borehole(
		borehole_id: str, 
		db = Depends(DBEngine.get_db), 
		):
	# if await crud.has_children(db, models.Run, borehole_id):
	# 	# check for permissions
	# 	raise HTTPException(status_code=403, detail="Cascade delete is not authorized")

	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	active_borehole_id = await crud.get_object_field(db, models.Well, well_id, 'borehole_id')

	if borehole_id == str(active_borehole_id):
		await crud.update_object(db, models.Well, well_id, {'borehole_id': None})

	await crud.cdelete_borehole(db, borehole_id)


@app.put("/{borehole_id}/active", 
    tags=["boreholes"],
    summary="Set active flag",
    dependencies=[Depends(Authorize(Action.borehole_write))]
)
async def set_active(
		borehole_id: str, 
		active: bool = Body(...), 
		db = Depends(DBEngine.get_db), 
		):
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	# TODO: check if borehole is last

	#check if exists active run
	if not active:
		if await crud.get_object_field(db, models.Borehole, borehole_id, 'run_id') is not None:
			raise HTTPException(status_code=403, detail="Borehole contains active run")

	await crud.update_object(db, models.Well, well_id, {'borehole_id': ObjectId(borehole_id) if active else None })

@app.post("/{borehole_id}/runs", 
    tags=["runs"],
    summary="Add new run to borehole",
    status_code=201,
    dependencies=[Depends(Authorize(Action.run_create))]
)
async def create_run(
		borehole_id: str, 
		response: Response, 
		d: dict = Depends(run_in_create), 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		):
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)

	#check if exists active run
	if await crud.get_object_field(db, models.Borehole, borehole_id, 'run_id') is not None:
		raise HTTPException(status_code=403, detail="Borehole contains active run")

	async with await dbc.start_session() as s:
		async with s.start_transaction():
			run_id = await create_run_impl(db, borehole_id, d, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	await calc_run(db, str(run_id))
	response.headers["Location"] = f'/runs/{run_id}'
	return run_id
