from datetime import datetime
from typing import Optional
from bson.objectid import ObjectId
from fastapi import HTTPException

from mwdstdb import crud, models
from mwdstdb.tasks import correction, update_calc_fields_well, update_calc_fields_borehole, update_calc_fields_run


async def ensure_manual_mode(db, well_id):
    well = await crud.get_object(db, models.Well, well_id)
    if well['data_mode'] == models.DataMode.workflow:
        raise HTTPException(status_code=403, detail="Manual API is disabled in workflow mode")
    if well['maintenance_mode']:
        raise HTTPException(status_code=403, detail="Manual API is disabled in maintenance mode")



async def create_borehole(db, well_id, b: dict, **kwargs):
    runs = b.pop('runs', []) or []
    borehole_id = await crud.create_child_object(db, models.Borehole, well_id, b, **kwargs)
    for r in runs:
        await create_run(db, borehole_id, r, **kwargs)
    return borehole_id


async def create_run(db, borehole_id, r: dict, **kwargs):
    surveys = r.pop('surveys', []) or []
    ci = r.pop('ci', None)
    plan = r.pop('plan', None)

    if ci is not None:
        ci_id = await crud.create_object(db, models.ContinuousInclination, {"stations": ci}, **kwargs)
        r['ci_id'] = ObjectId(ci_id)
    run_id = await crud.create_child_object(db, models.Run, borehole_id, r, **kwargs)
    if plan is not None:
        await crud.create_child_object(db, models.Plan, run_id, {**plan, 'uploaded': datetime.now()}, **kwargs)
    for s in surveys:
        await crud.create_child_object(db, models.Survey, run_id, s, **kwargs)
    return run_id


async def start_task(db, obj_id, type: str, autostart: bool = True):
    task = await crud.find_object(db, models.Task, {'parent_id': ObjectId(obj_id), 'type': type})
    if task is None:
        task_id = await crud.create_child_object(db, models.Task, obj_id, {
            'type': type,
            'status': models.TaskStatus.scheduled
        })
    elif task['status'] == models.TaskStatus.faulted or task['status'] == models.TaskStatus.completed:
        task_id = task['_id']
        await crud.update_object(db, models.Task, task_id, {
            'parent_id': task['parent_id'],
            'status': models.TaskStatus.scheduled
        })
    else:
        raise HTTPException(403, "Task is already running")
    if autostart:
        if type == 'correction':
            correction.apply_async(args=[str(task_id)], countdown = 1)
    return str(task_id)


async def calc_well(db, well_id):
    await clear_calc_fields_well(db, well_id)
    update_calc_fields_well.apply_async(args=[str(well_id)], countdown = 0)

async def calc_borehole(db, borehole_id):
    await clear_calc_fields_borehole(db, borehole_id)
    update_calc_fields_borehole.apply_async(args=[str(borehole_id)], countdown = 0)

async def calc_run(db, run_id, correction_task_id: Optional[str] = None):
    await clear_calc_fields_run(db, run_id)
    update_calc_fields_run.apply_async(args=[str(run_id), correction_task_id], countdown = 0)

async def clear_calc_fields_well(db, well_id):
    children = await crud.get_child_objects(db, models.Borehole, well_id)
    for c in children:
        await clear_calc_fields_borehole(db, c['_id'])

async def clear_calc_fields_borehole(db, borehole_id):
    children = await crud.get_child_objects(db, models.Run, borehole_id)
    await crud.delete_child_objects(db, models.Task, borehole_id)
    await crud.delete_object_fields(db, models.Borehole, borehole_id, ['last_depth'])
    for c in children:
        await clear_calc_fields_run(db, c['_id'])

async def clear_calc_fields_run(db, run_id):
    await crud.delete_child_objects(db, models.Task, run_id)
    await crud.delete_object_fields(db, models.Run, run_id, ['reference', 'stations', 'etag'])
