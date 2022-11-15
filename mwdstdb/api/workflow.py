from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Response
from bson.objectid import ObjectId
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.models.user import User
from mwdstdb.models.validation import validate_borehole, validate_ci
from .deps.auth import get_current_user
from .deps.actrl import Action, Authorize
from .deps.units import workflow_borehole_in, workflow_run_in, workflow_survey_in
from .core import calc_run, calc_borehole, create_run as create_run_impl, create_borehole as create_borehole_impl, start_task
from .deps import exists


async def ensure_workflow_mode(well_id, db = Depends(DBEngine.get_db)):
	well = await crud.get_object(db, models.Well, well_id)
	if well['data_mode'] == models.DataMode.manual:
		raise HTTPException(status_code=403, detail="Workflow API is disabled in manual mode")
	if well['maintenance_mode']:
		raise HTTPException(status_code=403, detail="Workflow API is disabled in maintenance mode")

async def get_active_borehole(well_id, db = Depends(DBEngine.get_db)):
	borehole_id = await crud.get_object_field(db, models.Well, well_id, 'borehole_id')
	if borehole_id is None:
		raise HTTPException(status_code=404, detail="Active borehole not found")
	return borehole_id
	
async def get_active_run(borehole_id = Depends(get_active_borehole), db = Depends(DBEngine.get_db)):
	run_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'run_id')
	if run_id is None:
		raise HTTPException(status_code=404, detail="Active run not found")
	return run_id

async def no_active_run(borehole_id = Depends(get_active_borehole), db = Depends(DBEngine.get_db)):
	run_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'run_id')
	if run_id is not None:
		raise HTTPException(status_code=403, detail="Borehole contains active run")


app = APIRouter(
	dependencies=[
		Depends(get_current_user),
		Depends(exists.well),
		Depends(ensure_workflow_mode),
	]
)


@app.post("/{well_id}/borehole", 
    tags=['workflow'],
    summary="Create new active borehole",
	dependencies=[Depends(Authorize(Action.workflow))]
)
async def create_borehole(
		well_id: str, 
		response: Response, 
		d: dict = Depends(workflow_borehole_in), 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		):
	borehole_id = await crud.get_object_field(db, models.Well, well_id, 'borehole_id')

	if borehole_id is not None:
		raise HTTPException(status_code=403, detail="Well already has an active borehole")

	async with await dbc.start_session() as s:
		async with s.start_transaction():
			borehole_id = await create_borehole_impl(db, well_id, d, session=s)
			await crud.update_object(db, models.Well, well_id, {'borehole_id': ObjectId(borehole_id)}, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	await calc_borehole(db, borehole_id)
	
	response.headers["Location"] = f'/boreholes/{borehole_id}'
	return borehole_id


@app.put("/{well_id}/borehole/finalized", 
    tags=['workflow'],
    summary="Finalize active borehole",
	dependencies=[
		Depends(no_active_run),
		Depends(Authorize(Action.workflow))
		]
)
async def finalize_borehole(
		well_id: str, 
		db = Depends(DBEngine.get_db), 
		):
	await crud.update_object(db, models.Well, well_id, {'borehole_id': None})
	


@app.post("/{well_id}/run", 
    tags=['workflow'],
    summary="Add new active run",
	dependencies=[
		Depends(no_active_run),
		Depends(Authorize(Action.workflow))
		]
)
async def create_run(
		well_id: str, 
		response: Response, 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		d: dict = Depends(workflow_run_in), 
		borehole_id = Depends(get_active_borehole)
		):
	async with await dbc.start_session() as s:
		async with s.start_transaction():
			run_id = await create_run_impl(db, borehole_id, d, session=s)
			await crud.update_object(db, models.Borehole, borehole_id, {'run_id': ObjectId(run_id)}, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	response.headers["Location"] = f'/wells/{well_id}/run'
	
	await calc_run(db, run_id)
	
	return run_id


@app.put("/{well_id}/run/finalized", 
    tags=['workflow'],
    summary="Finalize active run",
	dependencies=[Depends(Authorize(Action.workflow))]
)
async def finalize_run(
		db = Depends(DBEngine.get_db), 
		borehole_id = Depends(get_active_borehole),
		run_id = Depends(get_active_run)
		):
	await crud.update_object(db, models.Borehole, borehole_id, {'run_id': None})

async def add_survey_impl(calc: bool, db, dbc, d: dict, borehole_id, run_id, strict: bool = False):
	plan = d.get('plan')
	slides = d.get('slides')
	ci = d.get('ci')

	# check CI
	if not strict:
		if ci is not None:
			ci_id = await crud.get_object_field(db, models.Run, run_id, "ci_id")
			if ci_id is not None:
				cis = await crud.get_object_field(db, models.ContinuousInclination, ci_id, 'stations')
			else:
				cis = []
			cis = [*cis, *ci]
			try:
				validate_ci(cis)
			except ValidationError:
				ci = None
	#end CI check

	async with await dbc.start_session() as s:
		async with s.start_transaction():
			survey_id = await crud.create_child_object(db, models.Survey, run_id, d['survey'], session=s)
			survey_id = ObjectId(survey_id)
			if plan is not None:
				try:
					await crud.create_child_object(db, models.Plan, run_id, {**plan, 'uploaded': datetime.now(), 'survey_id': survey_id}, session=s)
				except DuplicateKeyError:
					raise HTTPException(status_code=400, detail="Duplicate plan revision")

			if slides is not None:
				for slide in slides:
					slide['survey_id'] = survey_id
				await crud.add_array_element(db, models.Run, run_id, 'slidesheet', slides, session=s)
				ld = await crud.get_borehole_last_depth(db, borehole_id, session=s)
				await crud.update_object(db, models.Borehole, borehole_id, {'last_depth': ld}, session=s)

			if ci is not None:
				for c in ci:
					c['survey_id'] = survey_id
				ci_id = await crud.get_object_field(db, models.Run, run_id, "ci_id", session=s)
				if ci_id is None:
					ci_id = await crud.create_object(db, models.ContinuousInclination, {"stations": ci}, session=s)
					await crud.update_object(db, models.Run, run_id, {'ci_id': ObjectId(ci_id)}, session=s)
				else:
					await crud.add_array_element(db, models.ContinuousInclination, ci_id, 'stations', ci, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	task_id = None
	if calc:
		try:
			task_id = await start_task(db, borehole_id, 'correction', False)
		except:
			pass

	await calc_run(db, run_id, task_id)


@app.post("/{well_id}/survey", 
    tags=['workflow'],
    summary="Add new survey to active run",
	dependencies=[Depends(Authorize(Action.workflow))]
)
async def add_survey(
		calc: bool = False, 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		d: dict = Depends(workflow_survey_in), 
		borehole_id = Depends(get_active_borehole),
		run_id = Depends(get_active_run)
		):
	await add_survey_impl(calc, db, dbc, d, borehole_id, run_id, True)

wf_def_app = APIRouter()

@wf_def_app.post("/survey", 
    tags=['workflow'],
    summary="Add new survey to active run in assigned well",
	dependencies=[Depends(Authorize(Action.workflow_default))]
)
async def add_survey_default(
		calc: bool = False, 
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		d: dict = Depends(workflow_survey_in), 
		user: User = Depends(get_current_user)
		):
	well_id = user.well
	if well_id is None: 
		raise HTTPException(status_code=404, detail="Assigned well not found")
	borehole_id = await get_active_borehole(well_id, db)
	run_id = await get_active_run(borehole_id, db)
	await add_survey_impl(calc, db, dbc, d, borehole_id, run_id)


rollback_app = APIRouter(
	dependencies=[
		Depends(get_current_user),
		Depends(exists.survey),
	]
)
@rollback_app.delete("/survey/{survey_id}", 
    tags=['workflow'],
    summary="Revert addition of workflow survey",
	dependencies=[Depends(Authorize(Action.workflow_rollback))]
)
async def rollback_add_survey(
		survey_id: str,
		db = Depends(DBEngine.get_db), 
		dbc = Depends(DBEngine.get_client), 
		):
	run_id = await crud.get_object_field(db, models.Survey, survey_id, 'parent_id')
	borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
	well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
	await ensure_workflow_mode(well_id, db)
	async with await dbc.start_session() as s:
		async with s.start_transaction():
			await crud.delete_object(db, models.Survey, survey_id, session=s)

			await crud.find_and_delete_object(db, models.Plan, {'parent_id': ObjectId(run_id), 'survey_id': ObjectId(survey_id)}, session=s)

			await crud.remove_array_element(db, models.Run, run_id, 'slidesheet', {'survey_id': ObjectId(survey_id)}, session=s)
			ld = await crud.get_borehole_last_depth(db, borehole_id, session=s)
			await crud.update_object(db, models.Borehole, borehole_id, {'last_depth': ld}, session=s)

			ci_id = await crud.get_object_field(db, models.Run, run_id, "ci_id", session=s)
			if ci_id is not None:
				await crud.remove_array_element(db, models.ContinuousInclination, ci_id, 'stations', {'survey_id': ObjectId(survey_id)}, session=s)
			try:
				await validate_borehole(db, borehole_id, session=s)
			except ValidationError as err:
				raise HTTPException(422, detail=err.errors())

	await calc_run(db, run_id)


