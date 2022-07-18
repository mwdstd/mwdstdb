from enum import Enum
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator

from .units import Angle, Diameter, Length, Mass

class BhaElementType(str, Enum):
    bit = 'bit'
    motor = 'motor'
    rss = 'rss'
    bend_sub = 'bend_sub'
    sub = 'sub'
    string_stabilizer = 'string_stabilizer'
    reamer = 'reamer'
    mwd = 'mwd'
    lwd = 'lwd'
    hwdc = 'hwdc'
    hwdp = 'hwdp'
    nmdc = 'nmdc'
    drill_pipe = 'drill_pipe'
    collar = 'collar'
    jar = 'jar'
    other = 'other'

class Material(str, Enum):
    aluminum = "aluminum" #nmag
    beryllium_copper = "beryllium_copper" #nmag
    chrome_alloy = "chrome_alloy" #mag
    composite = "composite" #nmag
    # other = "other" #nmag
    nm_steel = "nmsteel" #nmag
    plastic = "plastic" #nmag
    steel = "steel" #mag
    steel_alloy = "steel_alloy" #mag
    titanium = "titanium" #nmag

class Gender(str, Enum):
    pin = "pin"
    box = "box"

class Thread(BaseModel):
    size: float
    type: str
    gender: Gender


class BhaElement(BaseModel):
    type: BhaElementType
    description: Optional[str]
    sn: Optional[str]
    od: Diameter
    id: Diameter
    weight: Mass
    length: Length
    material: Material

class Blade(BaseModel):
    od: Diameter
    center_to_bit: Length
    length: Length

class BHA(BaseModel):
    structure: List[BhaElement]
    blades: List[Blade]
    tf_correction: Angle = None #SL >= 2 BHA has motor
    bend_angle: Angle = None #if no bend elements present
    bend_to_bit: Length = None #if no bend elements present
    dni_to_bit: Length = None #if no MWD elements present
    @validator('tf_correction', 'bend_angle', 'bend_to_bit', 'dni_to_bit', pre=True, always=True)
    def set_zero_on_none_or_absent(cls, v):
        return v or 0.

 
