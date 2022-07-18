from typing import List, Optional
from pydantic import BaseModel, Field
from .dbmodel import DBModelMixin, ObjectIdStr
from .station import Station

class Plan(BaseModel):
    _coll = 'plans'
    stations: List[Station]
    revision: int

class PlanDB(Plan, DBModelMixin):
    pass

