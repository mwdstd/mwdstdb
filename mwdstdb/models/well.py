from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, conint

from .dbmodel import DBModelMixin
from .units import Acceleration, Angle, Length
from .client import ClientDB
from .oilfield import OilfieldDB
from .pad import PadDB

class DataMode(str, Enum):
    workflow = 'workflow'
    manual = 'manual'

class NorthType(str, Enum):
    true = 'true'
    grid = 'grid'
#    magnetic = 'magnetic'

class GeomagModel(str, Enum):
    wmm = 'wmm'
    emm = 'emm'
    bggm = 'bggm'
    hdgm = 'hdgm'
    ifr1 = 'ifr1'
    ifr2 = 'ifr2'

class GravityModel(str, Enum):
    igf80 = 'igf80'
    manual = 'manual'

class GridModel(str, Enum):
    wgs84 = 'wgs84'
    manual = 'manual'


class Well(BaseModel):
    _coll = 'wells'
    name: str
    lat: Angle
    lon: Angle
    alt: Length
    north_type: NorthType = NorthType.true
    geomag: GeomagModel
    grav: GravityModel = GravityModel.igf80
    grav_value: Optional[Acceleration]
    grid: GridModel = GridModel.wgs84
    grid_value: Angle = 0.
    geo_datum: Optional[str]
    cartesian_northing: Optional[float]
    cartesian_easting: Optional[float]
    service_level: conint(ge=1, le=3) = 1
    data_mode: DataMode = DataMode.workflow
    maintenance_mode: bool = False


class WellDB(Well, DBModelMixin):
    pass

class WellParents(BaseModel):
    client: ClientDB
    field: OilfieldDB
    pad: PadDB

class WellInfo(WellDB, WellParents):
    pass

from .borehole import BoreholeDB, BoreholeCreate

class WellCreate(Well):
    boreholes: Optional[List[BoreholeCreate]]

from .user import User

class WellGet(WellInfo):
    boreholes: List[BoreholeDB]
    fes: List[User]
