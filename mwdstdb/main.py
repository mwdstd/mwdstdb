from typing import List
from os import environ

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from . import crud, models, rpc
from .database import DBEngine
from .api import router

rpc.start()
app = FastAPI()

fe_origin = environ.get("MWDSTD_ORIGIN")

if fe_origin is not None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[fe_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def create_db_client():
    # start client here and reuse in future requests
    DBEngine.start()

@app.on_event("shutdown")
async def shutdown_db_client():
    # stop your client here
    DBEngine.stop()

app.include_router(router)

