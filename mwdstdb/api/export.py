from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.models.well import GeomagModel
from .deps.auth import get_current_user
from .deps.units import convert_out
from .deps import exists

app = APIRouter(
	dependencies=[Depends(get_current_user)]
)

well_export_out = convert_out(models.WellCreate)
borehole_export_out = convert_out(models.BoreholeCreate)
run_export_out = convert_out(models.RunCreate)

@app.get("/wells/{well_id}", 
    tags=['export'],
    summary="Export well",
    response_model_by_alias=False,
    dependencies=[Depends(exists.well)]
)
async def export_borehole(
        well_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(well_export_out), 
        ):
    b = await crud.export_well(db, well_id)
    if(b['geomag'] == GeomagModel.wmm or b['geomag'] == GeomagModel.emm):
        for bh in b['boreholes']:
            bh['ref_head'] = None
            bh['ref_traj'] = None
    return conv(b)

@app.get("/boreholes/{borehole_id}", 
    tags=['export'],
    summary="Export borehole",
    response_model_by_alias=False,
    dependencies=[Depends(exists.borehole)]
)
async def export_borehole(
        borehole_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(borehole_export_out), 
        ):
    b = await crud.export_borehole(db, borehole_id)
    return conv(b)


@app.get("/runs/{run_id}", 
    tags=['export'],
    summary="Export run",
    response_model_by_alias=False,
    dependencies=[Depends(exists.run)]
)
async def export_run(
        run_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(run_export_out), 
        ):
    r = await crud.export_run(db, run_id)
    return conv(r)
