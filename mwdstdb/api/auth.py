from datetime import timedelta
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
# from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from mwdstdb import crud
from mwdstdb.models import User, UserBase, UserCreate
from mwdstdb.database import DBEngine
from mwdstdb.security import verify_password, hash_password
from .deps.auth import create_access_token


ACCESS_TOKEN_EXPIRE_MINUTES = 30000

app = APIRouter()

class Credentials(BaseModel):
    login: str
    password: str

class Params(BaseModel):
    provider: str
    args: Union[str, Credentials]

class Result(BaseModel):
    provider: str
    token: str

@app.post("/signin", 
    tags=["auth"],
    response_model_by_alias=False
)
async def sign_in(params: Params = Body(...), db = Depends(DBEngine.get_db)):
    user: UserBase = None
    if params.provider == 'mwdstd':
        try:
            dbuser = await crud.find_object(db, User, {'login': params.args.login})
            if not verify_password(dbuser['password'], params.args.password):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            user = UserBase(name=dbuser['name'], login=dbuser['login'])
        except:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    dbuser = await crud.find_object(db, User, {'login': user.login})
    if dbuser is None:
        user_id = await crud.create_object(db, User, user.dict())
    else:
        user_id = str(dbuser['_id'])

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user_id}, expires_delta=access_token_expires)

    return Result(provider=params.provider, token=token)


@app.post("/signinform", 
    tags=["auth"],
    response_model_by_alias=False
)
async def sign_in(form: OAuth2PasswordRequestForm = Depends(), db = Depends(DBEngine.get_db)):
    user: UserBase = None
    try:
        dbuser = await crud.find_object(db, User, {'login': form.username})
        if not verify_password(dbuser['password'], form.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = UserBase(name=dbuser['name'], login=dbuser['login'])
    except:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = str(dbuser['_id'])

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user_id}, expires_delta=access_token_expires)

    return {"access_token": token, "token_type": "bearer"}
