from typing import List
import importlib

from fastapi import APIRouter, Depends, HTTPException

from mwdstdb.database import DBEngine
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

@app.get("/versions/", 
    tags=["meta"],
    summary="Get version information of known components",
    dependencies=[]
)
async def get_versions(
        db = Depends(DBEngine.get_db), 
        ):
    return [
        {'name': 'mwdstdb', 'version': self_version, 'buildDate': 0, 'description': self_description, 'homepage': 'https://github.com/mwdstd/mwdstdb'},
        {'name': 'mwdstdcore', 'version': '0.5.0', 'buildDate': 0, 'description': 'MWD STD Basic calculation server', 'homepage': 'https://github.com/mwdstd/mwdstdcore'},
        {'name': 'mwdstdwits', 'version': '0.5.0', 'buildDate': 0, 'description': 'MWD STD WITS Service', 'homepage': 'https://github.com/mwdstd/mwdstdwits'}
    ]

