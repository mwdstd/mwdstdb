from typing import List
from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse

from mwdstdb import models
from mwdstdb.crud.events import global_event_generator, object_event_generator, task_event_generator
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps.actrl import Action, Authorize
from .deps import exists


app = APIRouter(
	dependencies=[
        Depends(get_current_user)
        ]
)

@app.get("/", 
    tags=["events"],
    summary="Global event stream",
    dependencies=[]
)
async def get_events_global(
        request: Request, 
        db = Depends(DBEngine.get_db)
        ):
    return EventSourceResponse(global_event_generator(request, db))

@app.get("/tasks", 
    tags=["tasks"],
    summary="Get tasks notifications"
)
async def get_events_tasks(request: Request, db = Depends(DBEngine.get_db)):
    return EventSourceResponse(task_event_generator(request, db))

@app.get("/tasks/{task_id}", 
    tags=["tasks"],
    summary="Get task event stream",
    dependencies=[Depends(exists.task)]
)
async def get_events_task(
        task_id: str, 
        request: Request, 
        db = Depends(DBEngine.get_db)
        ):
    return EventSourceResponse(task_event_generator(request, db, task_id))

@app.get("/runs/{run_id}", 
    tags=["runs"],
    summary="Get run event stream",
    dependencies=[
        Depends(exists.run),
        Depends(Authorize(Action.run_read))
        ]
)
async def get_events_run(
        run_id: str, 
        request: Request, 
        db = Depends(DBEngine.get_db)
        ):
    return EventSourceResponse(object_event_generator(models.Run, request, db, run_id))

@app.get("/runs/", 
    tags=["runs"],
    summary="Get runs event stream",
    dependencies=[
        ]
)
async def get_events_run(
        request: Request, 
        id: List[str] = Query(...), 
        db = Depends(DBEngine.get_db)
        ):
    return EventSourceResponse(object_event_generator(models.Run, request, db, None, id))
