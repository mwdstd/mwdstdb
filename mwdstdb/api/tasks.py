from typing import List, Optional
from fastapi import APIRouter, Depends, Response

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .core import start_task
from .deps.auth import get_current_user
from .deps import exists


app = APIRouter(
	dependencies=[
        Depends(get_current_user)
        ]
)


@app.post("/", 
    tags=["tasks"],
    summary="Schedule new calculation task",
    status_code=202,
)
async def schedule_task(
        parent_id: models.ObjectIdStr, 
        type: models.TaskType, 
        response: Response, 
        db = Depends(DBEngine.get_db), 
        ):
    task_id = await start_task(db, parent_id, type)            
    response.headers["Location"] = f'/tasks/{task_id}'
    return task_id

@app.get("/{task_id}", 
    tags=["tasks"],
    summary="Get task info",
    response_model=models.TaskDb,
    response_model_by_alias=False,
    dependencies=[Depends(exists.task)]
)
async def get_task(
        task_id: str, 
        db = Depends(DBEngine.get_db)
        ):
    return await crud.get_object(db, models.Task, task_id)


@app.get("/{task_id}/request", 
    tags=["tasks"],
    summary="Get task request data",
    dependencies=[Depends(exists.task)]
)
async def get_task_request(
        task_id: str, 
        db = Depends(DBEngine.get_db)
        ):
    return await crud.get_object_field(db, models.Task, task_id, 'request')

@app.get("/", 
    tags=["tasks"],
    summary="Get current task list",
    status_code=200,
    response_model=List[models.TaskDb],
    response_model_by_alias=False
)
async def get_all_tasks(
        parent_id: Optional[models.ObjectIdStr] = None,
        type: Optional[models.TaskType] = None,
        db = Depends(DBEngine.get_db),
        ):
    q = {}
    if parent_id is not None:
        q = {**q, 'parent_id': parent_id}
    if type is not None:
        q = {**q, 'type': type}
    res = await crud.get_all_objects(db, models.Task, q)
    return res

