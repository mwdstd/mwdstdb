from typing import Dict, List, Optional, Union
from pydantic import BaseModel
from .units import Acceleration, Angle, FineRatio, Length, MagneticInduction
from .station import CorrectedStation, Station, TfStation
from .reference import RefParams

class Position(BaseModel):
    tvd: Length
    ns: Length
    ew: Length

class PlanDeviation(Position):
    inc: Angle
    az: Angle

class QcBounds(RefParams):
    inc: Optional[Angle]
    az: Optional[Angle]

class Qc(BaseModel):
    g: bool
    b: bool
    dip: bool
    inc: Optional[bool]
    az: Optional[bool]

class ManualCorrectedSurvey(BaseModel):
    md: Length
    gx: Acceleration
    gy: Acceleration
    gz: Acceleration
    bx: MagneticInduction
    by: MagneticInduction
    bz: MagneticInduction
    qc: int
    min: Optional[QcBounds]
    max: Optional[QcBounds]
    qc_pass: Optional[Qc]

class CorrectedSurvey(ManualCorrectedSurvey):
    inc_pass: bool
    az_pass: bool

class QualityFactor(BaseModel):
    name: str
    value: Optional[bool] = None
    severity: Optional[int] = None

class DniParams(BaseModel):
    ABX: Acceleration
    ABY: Acceleration
    ABZ: Acceleration
    ASX: FineRatio
    ASY: FineRatio
    ASZ: FineRatio
    MBX: MagneticInduction
    MBY: MagneticInduction
    MBZ: MagneticInduction
    MSX: FineRatio
    MSY: FineRatio
    MSZ: FineRatio
    MXY: Angle
    MXZ: Angle
    MYZ: Angle

class DniUnc(DniParams):
    pass

class ManualCorrectionResult(BaseModel):
    surveys: List[ManualCorrectedSurvey]
    stations: List[Union[CorrectedStation, TfStation]]
    stations_hd: Optional[List[TfStation]]
    sag: Optional[List[Angle]] = None
    qa: Dict[str, QualityFactor]
    dni_cs: Optional[DniParams] #temp optional while DB is not updated
    deepest: Optional[Station]
    plan_dev: Optional[Station]


class CorrectionResult(ManualCorrectionResult):
    surveys: List[CorrectedSurvey]
    apr_unc: Optional[DniUnc] #temp optional while DB is not updated
    apst_unc: Optional[DniUnc] #temp optional while DB is not updated
    ref_cs: Optional[RefParams] #temp optional while DB is not updated
    ref_unc: Optional[RefParams] #temp optional while DB is not updated

class CorrectionGet(BaseModel):
    _coll = 'corrections'
    result: Optional[Union[CorrectionResult, ManualCorrectionResult]]
