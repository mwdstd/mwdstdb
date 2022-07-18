from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from .dbmodel import DBModelMixin
from .units import Acceleration, Length, MagneticInduction, Mass, Temperature
from .run import RunDB, RunParents
from .plan import Plan

class Survey(BaseModel):
	_coll = 'surveys'
	md: Length
	gx: Acceleration
	gy: Acceleration
	gz: Acceleration
	bx: MagneticInduction
	by: MagneticInduction
	bz: MagneticInduction
	time: datetime
	temp: Optional[Temperature]
	pre_qc: bool
	ds_weight_up: Optional[Mass]
	ds_weight_down: Optional[Mass]
	ds_weight_rot: Optional[Mass]
	visible: bool = True

class SurveyDB(Survey, DBModelMixin):
	pass

class SurveyParents(RunParents):
    run: RunDB

class SurveyGet(SurveyDB, SurveyParents):
	pass

from .station import CiStation

class WorkflowSurvey(BaseModel):
	survey: Survey
	ci: Optional[List[CiStation]]
	plan: Optional[Plan]
