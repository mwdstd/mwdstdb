from typing import List, Optional
from enum import Enum
from pydantic import BaseModel
from .dbmodel import DBModelMixin


class Client(BaseModel):
    _coll = 'clients'
    name: str
    tag: Optional[str]

class ClientDB(Client, DBModelMixin):
    pass
    
from .oilfield import OilfieldDB

class ClientGet(ClientDB):
    oilfields: List[OilfieldDB]

