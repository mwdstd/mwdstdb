from enum import Enum
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Response
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel

from mwdstdb import crud
from mwdstdb.database import DBEngine
from mwdstdb.models import User, UserCreate, Role, Pad, Well
from mwdstdb.models.dbmodel import ObjectIdStr
from mwdstdb.security import hash_password, verify_password
from .deps.auth import get_current_user
from .deps import exists


app = APIRouter()
access_denied = HTTPException(status_code=403, detail="Access denied")

@app.get("/me",
    response_model_by_alias=False,
    response_model=User
)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


class PasswordChange(BaseModel):
    old_password: str
    new_password: str

@app.put("/me/pass")
async def change_password(
        pc: PasswordChange, 
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db)
        ):
    dbuser = await crud.find_object(db, User, {'login': current_user.login})
    if verify_password(dbuser['password'], pc.old_password):
        await crud.update_object(db, User, current_user.id, {'password': hash_password(pc.new_password)})
    else:
        raise HTTPException(403, 'Invalid password')


@app.put("/me/us")
async def set_user_unit_system(
        us: dict, 
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db)
        ):
    await crud.update_object(db, User, current_user.id, {'us': us})


@app.post("/", 
    tags=["users"],
    summary="Register new user",
    status_code=201,
)
async def create_user(
        user: UserCreate, 
        response: Response, 
        db = Depends(DBEngine.get_db), 
        current_user: User = Depends(get_current_user)
        ):
    
    if current_user.role not in [Role.SU, Role.DE]:
        raise access_denied
    try:
        user.password = hash_password(user.password)
        id = await crud.create_object(db, User, user.dict())
        response.headers["Location"] = f'/users/{id}'
        return id
    except DuplicateKeyError:
        raise HTTPException(status_code=403, detail="User already exists")


@app.get("/",
    response_model_by_alias=False,
    response_model=List[User]
)
async def get_available_users(
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db)
        ):
    if current_user.role == Role.SU:
        users = await crud.get_all_objects(db, User)
        return users
    if current_user.role == Role.DE:
        return await crud.get_all_objects(db, User, {
            '$or': [
                {'role': None}, 
                {'role': Role.FE}
            ]
        })
    return []

@app.get("/{user_id}",
    response_model_by_alias=False,
    response_model=User, 
    dependencies=[Depends(exists.user)]
)
async def get_user(
        user_id: str,
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db)
        ):
    user = await crud.get_object(db, User, user_id)
    return user

@app.delete("/{user_id}", 
    tags=["users"],
    summary="Delete user",
    dependencies=[Depends(exists.user)]
)
async def delete_user(
        user_id: str, 
        db = Depends(DBEngine.get_db), 
        current_user: User = Depends(get_current_user),
        ):
    
    if current_user.role != Role.SU:
        raise access_denied

    # can't delete self 
    if user_id == str(current_user.id):
        raise access_denied

    await crud.delete_object(db, User, user_id)

@app.put('/{user_id}/role',
    summary="Assign user role",
    dependencies=[Depends(exists.user)]
)
async def assign_user_role(
        user_id: str,
        role: Optional[Role] = Body(None),
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db)
        ):
    
    # can't change own role
    if user_id == str(current_user.id):
        raise access_denied
    
    # access denied to FE & DM
    if current_user.role == Role.FE or current_user.role == Role.CR:
        raise access_denied

    if current_user.role == Role.DE:
        # can grant only FE
        if role != Role.FE:
            raise access_denied

        # can't revoke
        if role is None:
            raise access_denied
    
    await crud.update_object(db, User, user_id, {'role': role})


@app.put('/{user_id}/client',
    summary="Assign CR to client",
    dependencies=[Depends(exists.user)]
)
async def assign_fe_to_well(
        user_id: str,
        client_id: ObjectIdStr = Body(None),
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db),
        ):
    
    if current_user.role not in [Role.SU]:
        raise access_denied
    
    target_user = User.parse_obj(await crud.get_object(db, User, user_id))
    # client assignment works only for CR
    if target_user.role != Role.CR:
        raise access_denied

    if client_id is not None and not await exists.client(client_id, db):
        raise HTTPException(status_code=404, detail='Client not found')

    await crud.update_object(db, User, user_id, {'client': client_id})


@app.put('/{user_id}/fields',
    summary="Assign DE to fields",
    dependencies=[Depends(exists.user)]
)
async def assign_de_to_fields(
        user_id: str,
        fields: Optional[List[ObjectIdStr]] = Body([]),
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db)
        ):
    
    if current_user.role != Role.SU:
        raise access_denied
    
    target_user = User.parse_obj(await crud.get_object(db, User, user_id))
    # field assignment works only for DE
    if target_user.role != Role.DE:
        raise access_denied
    
    fields = list(set(fields))
    # check oilfield existance
    if not all([await exists.oilfield(fid, db) for fid in fields]):
        raise HTTPException(status_code=422, detail='Oilfield not found')

    await crud.update_object(db, User, user_id, {'oilfields': fields})


from pydantic import BaseModel

class OperationType(str, Enum):
    add = 'add'
    remove = 'remove'

class Operation(BaseModel):
    type: OperationType
    object_id: ObjectIdStr

@app.put('/{user_id}/well',
    summary="Assign FE to well",
    dependencies=[Depends(exists.user)]
)
async def assign_fe_to_well(
        user_id: str,
        well_id: ObjectIdStr = Body(None),
        current_user: User = Depends(get_current_user),
        db = Depends(DBEngine.get_db),
        ):
    
    if current_user.role not in [Role.SU, Role.DE]:
        raise access_denied
    
    target_user = User.parse_obj(await crud.get_object(db, User, user_id))
    # well assignment works only for FE
    if target_user.role != Role.FE:
        raise access_denied

    if well_id is not None:
        if not await exists.well(well_id, db):
            raise HTTPException(status_code=404, detail='Well not found')
        if current_user.role == Role.DE:
            # check DE permissions
            pad_id = await crud.get_object_field(db, Well, well_id, 'parent_id')
            of_id = await crud.get_object_field(db, Pad, pad_id, 'parent_id')
            if of_id not in current_user.oilfields:
                raise access_denied
    await crud.update_object(db, User, user_id, {'well': well_id})
