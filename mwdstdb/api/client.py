from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps.units import oilfield_in
from .deps.actrl import Action, Authorize
from .deps import exists

app = APIRouter(
	dependencies=[Depends(get_current_user)]
)

@app.post("/", 
    tags=["clients"],
    summary="Register new client company",
    status_code=201,
    dependencies=[Depends(Authorize(Action.client_create))]
)
async def create_client(
        client: models.Client, 
        response: Response, 
        db = Depends(DBEngine.get_db), 
        current_user: models.User = Depends(get_current_user)
        ):
    id = await crud.create_object(db, models.Client, {**client.dict(), 'owner': current_user.id})
    response.headers["Location"] = f'/clients/{id}'
    return id

@app.get("/", 
    tags=["clients"],
    summary="Get list of client companies",
    response_model=List[models.ClientDB],
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.client_read))]
)
async def get_clients(
        db = Depends(DBEngine.get_db), 
        current_user: models.User = Depends(get_current_user)
        ):
    return await crud.get_all_objects(db, models.Client)

@app.get("/{client_id}", 
    tags=["clients"],
    summary="Get client company information",
    response_model=models.ClientGet,
    response_model_by_alias=False,
    dependencies=[
        Depends(exists.client),
        Depends(Authorize(Action.client_read))
        ]
)
async def get_client(
        client_id: str, 
        db = Depends(DBEngine.get_db), 
        ):
    return await crud.get_client(db, client_id)


@app.put("/{client_id}", 
    tags=["clients"],
    summary="Update client company information",
    dependencies=[
        Depends(exists.client),
        Depends(Authorize(Action.client_write))
        ]
)
async def update_client(
        client_id: str, 
        client: models.Client, 
        db = Depends(DBEngine.get_db), 
        ):
    await crud.update_object(db, models.Client, client_id, client.dict())

@app.delete("/{client_id}", 
    tags=["clients"],
    summary="Delete client company",
    dependencies=[
        Depends(exists.client),
        Depends(Authorize(Action.client_delete))
        ]
)
async def delete_client(
        client_id: str, 
        cascade: bool = False, 
        db = Depends(DBEngine.get_db), 
        ):
    if not cascade and await crud.has_children(db, models.Oilfield, client_id):
        # check for permissions
        raise HTTPException(status_code=403, detail="Cascade delete is not authorized")
    await crud.cdelete_client(db, client_id)

@app.post("/{client_id}/fields", 
    tags=["fields"],
    summary="Add new client owned oilfield",
    status_code=201,
    dependencies=[
        Depends(exists.client),
        Depends(Authorize(Action.oilfield_create))
        ]
)
async def create_field(
        client_id: str, 
        response: Response, 
        d: dict = Depends(oilfield_in), 
        db = Depends(DBEngine.get_db), 
        ):
    id = await crud.create_child_object(db, models.Oilfield, client_id, d)
    response.headers["Location"] = f'/fields/{id}'
    return id