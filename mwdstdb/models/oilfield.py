from typing import List, Optional
from pydantic import BaseModel, Field
from .dbmodel import DBModelMixin
from .client import ClientDB
from .units import Angle, Length

class Oilfield(BaseModel):
    _coll = 'oilfields'
    name: str
    lat: Angle
    lon: Angle
    alt: Optional[Length]
    dlat: Angle = 1.0
    dlon: Angle = 1.0
    dalt: Length = 300.

class OilfieldDB(Oilfield, DBModelMixin):
    pass

class OilfieldParents(BaseModel):
    client: ClientDB

from .pad import PadDB

class OilfieldGet(OilfieldDB, OilfieldParents):
    pads: List[PadDB]
