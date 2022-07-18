from typing import Optional
from pydantic import BaseModel
from .units import Angle, Diameter, Length

class Section(BaseModel):
    # stop_depth: Length
    hole_diameter: Diameter
    casing_inner_diameter: Optional[Diameter] #optional for last open-hole section
    casing_start: Optional[Length] #optional for last open-hole section
    casing_stop: Optional[Length] #optional for last open-hole section
    description: Optional[str]