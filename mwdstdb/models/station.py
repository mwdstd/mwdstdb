from typing import Optional
from pydantic import BaseModel

from .units import Acceleration, Angle, Length, MagneticInduction

class CiStation(BaseModel):
	md: Length
	inc: Angle

class Station(CiStation):
	az: Angle
	tvd: Optional[Length]
	ns: Optional[Length]
	ew: Optional[Length]

class TfStation(Station):
	tf: Optional[Angle]

class FullStation(TfStation):
	tg: Acceleration
	tb: MagneticInduction
	dip: Angle

class CorrectedStation(FullStation):
	dmd: Optional[Length]
	dinc: Optional[Angle]
	daz: Optional[Angle]
