from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, validator

from .dbmodel import DBModelMixin
from .units import Angle, Density, Length, Ratio
from .borehole import BoreholeDB, BoreholeParents
from .plan import Plan, PlanDB
from .section import Section
from .bha import BHA
from .correction import CorrectionGet
from .station import CiStation, FullStation
from .reference import Reference


class Equipment(BaseModel):
    sn: Optional[str]
    name: Optional[str]

class Tool(Equipment):
    dni: Equipment
    tf_correction: Angle = 0.

class ContinuousInclination(BaseModel):
    _coll = 'ci'
    __root__: List[CiStation] = []

class Run(BaseModel):
    _coll = 'runs'
    name: str
    tool: Tool
    toolcode: str = 'MWD_Rev4'
    bha: Optional[BHA] #SL >= 2 (1 for EDI estimation)
    mud_weight: Optional[Density] #SL >= 2
    geometry: Optional[List[Section]] #SL >= 4
    status_msa: bool = True

class RunDB(Run, DBModelMixin):
    active: bool = False

class RunShort(RunDB):
    correction: Optional[CorrectionGet]

class RunParents(BoreholeParents):
    borehole: BoreholeDB

from .survey import Survey, SurveyDB

class RunUpdate(Run):
    pass

class RunCreate(RunUpdate):
    ci: Optional[ContinuousInclination] = None #SL >=3
    surveys: Optional[List[Survey]]
    plan: Plan

class RunCreateWorkflow(RunUpdate):
    plan: Plan

class RunGet(RunDB, RunParents):
    plan: PlanDB
    surveys: List[SurveyDB]
    stations: Optional[List[FullStation]]
    head_ref: Optional[Reference]
    reference: Optional[List[Reference]]
    ci: Optional[List[CiStation]] = None
    correction: Optional[CorrectionGet]
    

