from pydantic import BaseModel

from .units import Acceleration, Angle, Length, MagneticInduction


class MagRef(BaseModel):
    b: MagneticInduction
    dip: Angle
    dec: Angle

class MagRefPoint(MagRef):
    md: Length

class RefParams(BaseModel):
    g: Acceleration
    b: MagneticInduction
    dip: Angle

class Reference(RefParams):
    g: Acceleration
    b: MagneticInduction
    dip: Angle
    dec: Angle
    grid: Angle
