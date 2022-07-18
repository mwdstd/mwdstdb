from typing import Iterable, List, Union
import base64
import json
import traceback
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status

from mwdstdb.utils import convert_units, convert_units_bm_to_dict
from mwdstdb.models.dbmodel import DBModelMixin
from mwdstdb.models.units import StorageUnitSystem
from .auth import get_current_user
from mwdstdb import models


def get_client_unit_system(us: str = None, user: models.User = Depends(get_current_user)):
    if us is None:
        return user.us
    try:
        us_dict = json.loads(base64.b64decode(us).decode('utf-8'))
        return us_dict
    except:
        traceback.print_exc()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Failed to parse unit system")

def convert_in(us: dict = Depends(get_client_unit_system)):
    def converter(obj: Union[BaseModel, Iterable[BaseModel]], target_us: dict = StorageUnitSystem):
        return convert_units_bm_to_dict(obj, us, target_us)
    return converter

replace_object_ids = {**DBModelMixin.Config.json_encoders}
def convert_out(modelType):
    def dependency(us: dict = Depends(get_client_unit_system)):
        def converter(obj: dict, source_us: dict = StorageUnitSystem):
            return convert_units(modelType, obj, source_us, us, replace_object_ids)
        return converter
    return dependency

def oilfield_in(oilfield: models.Oilfield, conv = Depends(convert_in)) -> dict:
    return conv(oilfield)

def pad_in(pad: models.Pad, conv = Depends(convert_in)) -> dict:
    return conv(pad)

def well_in_create(well: models.WellCreate, conv = Depends(convert_in)) -> dict:
    return conv(well)

def well_in_update(well: models.Well, conv = Depends(convert_in)) -> dict:
    return conv(well)

def borehole_in_create(borehole: models.BoreholeCreate, conv = Depends(convert_in)) -> dict:
    return conv(borehole)

def borehole_in_update(borehole: models.Borehole, conv = Depends(convert_in)) -> dict:
    return conv(borehole)

def plan_in(plan: models.Plan, conv = Depends(convert_in)) -> dict:
    return conv(plan)

def sections_in(sections: List[models.Section], conv = Depends(convert_in)) -> list:
    return [conv(v) for i, v in enumerate(sections)]

def run_in_create(run: models.RunCreate, conv = Depends(convert_in)) -> dict:
    return conv(run)

def run_in_update(run: models.RunUpdate, conv = Depends(convert_in)) -> dict:
    return conv(run)

def ci_in(ci_stations: models.ContinuousInclination, conv = Depends(convert_in)) -> list:
    return conv(ci_stations)

def survey_in(survey: models.Survey, conv = Depends(convert_in)) -> dict:
    return conv(survey)

def surveys_in(surveys: List[models.Survey], conv = Depends(convert_in)) -> dict:
    return [conv(v) for v in surveys]

def plan_in(plan: models.Plan, conv = Depends(convert_in)) -> dict:
    return conv(plan)

def workflow_borehole_in(survey: models.Borehole, conv = Depends(convert_in)) -> dict:
    return conv(survey)

def workflow_run_in(run: models.RunCreateWorkflow, conv = Depends(convert_in)) -> dict:
    return conv(run)

def workflow_survey_in(survey: models.WorkflowSurvey, conv = Depends(convert_in)) -> dict:
    return conv(survey)
