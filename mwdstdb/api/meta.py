from typing import List
import importlib

from fastapi import APIRouter, Depends, HTTPException

from mwdstdb import rpc
from .deps.auth import get_current_user


app = APIRouter(
	dependencies=[
        Depends(get_current_user)
        ]
)

try:
    self_version = importlib.metadata.version('mwdstdb')
    self_description = importlib.metadata.metadata('mwdstdb')['Summary']
except:
    import tomlkit
    with open('pyproject.toml') as pyproject:
        file_contents = pyproject.read()

    content = tomlkit.parse(file_contents)['tool']['poetry']
    self_version = f'{content["version"]}-dev'
    self_description = content['description']

core_info = None

@app.get("/versions/", 
    tags=["meta"],
    summary="Get version information of known components",
    dependencies=[]
)
async def get_versions(
        ):
    global core_info
    if core_info is None:
        try:
            core_info = (await rpc.get('v1/ver')).json()
        except:
            core_info = None
    return [x for x in [
        {'name': 'mwdstdb', 'version': self_version, 'buildDate': 0, 'description': self_description, 'homepage': 'https://github.com/mwdstd/mwdstdb'},
        core_info,
        {'name': 'mwdstdwits', 'version': 'N/A', 'buildDate': 0, 'description': 'MWD STD WITS Service', 'homepage': 'https://github.com/mwdstd/mwdstdwits'}
    ] if x is not None]

