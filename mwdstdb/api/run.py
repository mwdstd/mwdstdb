from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, Body
from pydantic import ValidationError
from bson.objectid import ObjectId
from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.models.validation import validate_borehole
from .core import ensure_manual_mode, calc_run
from .deps.auth import get_current_user
from .deps.units import convert_out, run_in_update, ci_in, plan_in, survey_in, surveys_in
from .deps.actrl import Action, Authorize
from .deps import exists

app = APIRouter(
	dependencies=[
		Depends(get_current_user),
		Depends(exists.run)
		]
)

run_out = convert_out(models.RunGet)

@app.get("/{run_id}", 
    tags=["runs"],
    summary="Get run information",
#    response_model=models.RunGet,
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.run_read))]
)
async def get_run(
		run_id: str, 
		filter: bool = True, 
		db = Depends(DBEngine.get_db), 
		conv = Depends(run_out), 
		):
	r = await crud.get_run(db, run_id, filter)
	return conv(r)



@app.put("/{run_id}", 
    tags=["runs"],
    summary="Update run information",
    dependencies=[Depends(Authorize(Action.run_write))]
)
async def update_run(
		run_id: str, 
		d: dict = Depends(run_in_update), 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		):
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)

	async with await dbc.start_session() as s:
		async with s.start_transaction():
			await crud.update_object(db, models.Run, run_id, d, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	await calc_run(db, run_id)


@app.delete("/{run_id}", 
    tags=["runs"],
    summary="Delete run",
    dependencies=[Depends(Authorize(Action.run_delete))]
)
async def delete_run(
		run_id: str, 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		):
	# if await crud.has_children(db, models.Survey, run_id):
	# 	# check for permissions
	# 	raise HTTPException(status_code=403, detail="Cascade delete is not authorized")

	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)

	async with await dbc.start_session() as s:
		async with s.start_transaction():
			active_run_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'run_id', session=s)
			if run_id == str(active_run_id):
				await crud.update_object(db, models.Borehole, borehole_id, {'run_id': None}, session=s)
			elif active_run_id is not None:
				raise HTTPException(status_code=403, detail="Borehole contains active run")

			await crud.cdelete_run(db, run_id, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())


@app.put("/{run_id}/ci", 
    tags=["runs"],
    summary="Set continuous inclination stations of selected run",
    dependencies=[Depends(Authorize(Action.run_write))]
)
async def set_ci(
		run_id: str, 
		d: List[dict] = Depends(ci_in), 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		):
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	ci_id = await crud.get_object_field(db, models.Run, run_id, "ci_id")

	async with await dbc.start_session() as s:
		async with s.start_transaction():
			if ci_id is None:
				ci_id = await crud.create_object(db, models.ContinuousInclination, {"stations": d.get('__root__')}, session=s)
				await crud.update_object(db, models.Run, run_id, {'ci_id': ObjectId(ci_id)}, session=s)
			else:
				await crud.update_object(db, models.ContinuousInclination, ci_id, {"stations": d.get('__root__')}, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	await calc_run(db, run_id)


@app.put("/{run_id}/plan", 
    tags=["runs"],
    summary="Upload new plan revision",
    dependencies=[Depends(Authorize(Action.run_write))]
)
async def set_plan(
		run_id: str, 
		d: dict = Depends(plan_in), 
		db = Depends(DBEngine.get_db), 
		):
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	try:
		await crud.create_child_object(db, models.Plan, run_id, {**d, 'uploaded': datetime.now()})
	except DuplicateKeyError:
		raise HTTPException(status_code=400, detail="Duplicate plan revision")
	await calc_run(db, run_id)


@app.put("/{run_id}/active", 
    tags=["runs"],
    summary="Set active flag",
    dependencies=[Depends(Authorize(Action.run_write))]
)
async def set_active(
		run_id: str, 
		active: bool = Body(...), 
		db = Depends(DBEngine.get_db), 
		):
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	act_borehole_id = await crud.get_object_field(db, models.Well, well_id, 'borehole_id')
	if borehole_id != act_borehole_id:
		raise HTTPException(status_code=403, detail="Run borehole is not active")
	# TODO: check if run is last
	last_run = await crud.get_child_objects(db, models.Run, borehole_id, limit=1, sort=[('_id', DESCENDING)])
	if str(last_run[0]['_id']) != run_id:
		raise HTTPException(status_code=403, detail="Only last run can be activated")
	# TODO: validation

	await crud.update_object(db, models.Borehole, borehole_id, {'run_id': ObjectId(run_id) if active else None })

@app.post("/{run_id}/surveys", 
    tags=["surveys"],
    summary="Add new survey to run",
    status_code=201,
    dependencies=[Depends(Authorize(Action.survey_create))]
)
async def create_survey(
        run_id: str, 
        response: Response, 
        d: dict = Depends(survey_in), 
        db = Depends(DBEngine.get_db), 
        ):
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	id = await crud.create_child_object(db, models.Survey, run_id, d)
	await calc_run(db, run_id)
	response.headers["Location"] = f'/surveys/{id}'
	return id

@app.put("/{run_id}/surveys", 
    tags=["surveys"],
    summary="Replace run surveys with provided batch",
    status_code=200,
    dependencies=[Depends(Authorize(Action.survey_import))]
)
async def import_surveys(
        run_id: str, 
        surveys: List[dict] = Depends(surveys_in), 
        db = Depends(DBEngine.get_db), 
        ):
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_manual_mode(db, well_id)
	await crud.delete_child_objects(db, models.Survey, run_id)
	for s in surveys:
		await crud.create_child_object(db, models.Survey, run_id, s)
	await calc_run(db, run_id)
