from typing import List

from fastapi import APIRouter, Depends, HTTPException

from mwdstdb.database import DBEngine
from .deps.auth import get_current_user


app = APIRouter(
	dependencies=[
        Depends(get_current_user)
        ]
)

@app.get("/versions/", 
    tags=["meta"],
    summary="Get version information of known components",
    dependencies=[]
)
async def get_versions(
        db = Depends(DBEngine.get_db), 
        ):
    return [
        {'name': 'mwdstdb', 'version': '0.5.1', 'buildDate': 0, 'description': 'MWD STD Basic data storage and automation backend', 'homepage': 'https://github.com/mwdstd/mwdstdb'},
        {'name': 'mwdstdcore', 'version': '0.5.0', 'buildDate': 0, 'description': 'MWD STD Basic calculation server', 'homepage': 'https://github.com/mwdstd/mwdstdcore'},
        {'name': 'mwdstdwits', 'version': '0.5.0', 'buildDate': 0, 'description': 'MWD STD WITS Service', 'homepage': 'https://github.com/mwdstd/mwdstdwits'}
    ]

