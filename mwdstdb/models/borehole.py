from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, validator

from .dbmodel import DBModelMixin
from .units import Length
from .well import WellDB, WellParents, GeomagModel
from .plan import Plan
from .reference import MagRef, MagRefPoint
from .section import Section


class Interval(BaseModel):
	start: Length
	stop: Length

def empty_list_on_none(v):
    return v or []

class Borehole(BaseModel):
    _coll = 'boreholes'
    name: str
    kick_off: Length = 0.
    rkb_elevation: Length = 0.
    ref_head: Optional[MagRef]
    ref_traj: Optional[List[MagRefPoint]]
    start_date: datetime
    interference_intervals: Optional[List[Interval]]
    geometry: Optional[List[Section]] #SL >= 4

    _ii = validator("interference_intervals", pre=True, always=True, allow_reuse=True)(empty_list_on_none)

    @classmethod
    def validate_ref(cls, src: dict, geomag: GeomagModel):
        class ValidateRef(BaseModel):
            ref_head: Optional[MagRef]
            ref_traj: Optional[List[MagRefPoint]]
            @validator('ref_head', allow_reuse=True)
            def v_ref_head(cls, value):
                if geomag == GeomagModel.emm or geomag == GeomagModel.wmm:
                    if value is not None:
                        raise ValueError('Nonempty reference for automatic calculation')
                elif geomag == GeomagModel.bggm or geomag == GeomagModel.hdgm:
                    if value is None:
                        raise ValueError('Empty external reference')
            @validator('ref_traj', allow_reuse=True)
            def v_ref_traj(cls, value):
                if geomag == GeomagModel.emm or geomag == GeomagModel.wmm:
                    if value is not None:
                        raise ValueError('Nonempty reference for automatic calculation')
                elif geomag == GeomagModel.ifr1 or geomag == GeomagModel.ifr2:
                    if value is None or len(value) == 0:
                        raise ValueError('Empty external reference')
        check = ValidateRef(ref_head=src['ref_head'], ref_traj=src['ref_traj'])



class BoreholeDB(Borehole, DBModelMixin):
    active: bool = False
    last_depth: Optional[Length] = None

class BoreholeParents(WellParents):
    well: WellDB

from .run import RunCreate, RunShort

class BoreholeCreate(Borehole):
    runs: Optional[List[RunCreate]]

class BoreholeGet(BoreholeDB, BoreholeParents):
    runs: List[RunShort]
    geometry_finished: List[Section] = []
    last_plan: Optional[Plan]
    
    _gf = validator("geometry_finished", pre=True, always=True, allow_reuse=True)(empty_list_on_none)
