from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mwdstdb import crud
from mwdstdb import models
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps.units import convert_out

class PlanInfo(BaseModel):
    revision: int
    uploaded: Optional[datetime]
    length: Optional[int]

class ActiveRunsInfo(BaseModel):
    client: models.ClientDB
    field: models.OilfieldDB
    pad: models.PadDB
    well: models.WellDB
    borehole: models.BoreholeDB
    run: models.RunDB
    correction: Optional[models.CorrectionGet]
    plan: Optional[PlanInfo]

app = APIRouter(
)
control_runs_out = convert_out(List[ActiveRunsInfo])

@app.get("/list/", 
    tags=["control"],
    summary="Get workitems list",
    response_model_by_alias=False
)
async def get_list(
        db = Depends(DBEngine.get_db), 
        conv = Depends(control_runs_out), 
        current_user = Depends(get_current_user)
        ):
    if current_user.role == models.Role.SU:
        query = {}
    elif current_user.role == models.Role.CR:
        query = {'client._id': current_user.client}
    elif current_user.role == models.Role.DE:
        query = {'field._id': {'$in': current_user.oilfields}}
    else:
        raise HTTPException(status_code=403, detail="Access denied")

    w = await crud.get_active_runs(db, query)
    res = conv(w)
    return res
