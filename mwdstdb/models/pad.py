from enum import Enum
from typing import List
from datetime import datetime
from pydantic import BaseModel
from .dbmodel import DBModelMixin
from .client import ClientDB
from .oilfield import OilfieldDB
from .units import Angle, Length

class PadType(str, Enum):
    land = 'land'
    offshore = 'offshore'

class Pad(BaseModel):
    _coll = 'pads'
    name: str
    type: PadType
    lat: Angle
    lon: Angle
    alt: Length
    dlat: Angle = 0.5
    dlon: Angle = 0.5
    dalt: Length = 300.
    date_start: datetime
    date_finish: datetime


class PadDB(Pad, DBModelMixin):
    pass

class PadParents(BaseModel):
    client: ClientDB
    field: OilfieldDB

from .well import WellDB

class PadGet(PadDB, PadParents):
    wells: List[WellDB]
