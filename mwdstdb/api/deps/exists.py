from bson.errors import InvalidId
from fastapi import Depends, HTTPException

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .utils import get_resource_id

not_found = HTTPException(status_code=404, detail='Not found')

class Exists():
    def __init__(self, model_type):
        self.model_type = model_type
    async def __call__(self, res_id = Depends(get_resource_id), db = Depends(DBEngine.get_db)):
        try:
            await crud.get_object_field(db, self.model_type, res_id, '_id')
            return True
        except (InvalidId, KeyError):
            raise not_found       

client = Exists(models.Client)
oilfield = Exists(models.Oilfield)
pad = Exists(models.Pad)
well = Exists(models.Well)
borehole = Exists(models.Borehole)
run = Exists(models.Run)
survey = Exists(models.Survey)
task = Exists(models.Task)
user = Exists(models.User)
