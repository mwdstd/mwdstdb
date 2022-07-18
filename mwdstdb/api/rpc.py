from typing import List, Optional, Union
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx

from mwdstdb import crud
from mwdstdb import models
from mwdstdb import rpc
from mwdstdb.models.units import Angle, CalculationUnitSystem
from mwdstdb.database import DBEngine
from .deps.auth import get_current_user
from .deps.units import convert_out, convert_in
from .deps import exists
from .deps.actrl import Action, Authorize


class ManualCorrectionArgs(BaseModel):
    dni_cs: models.DniParams
    ref_cs: Optional[models.RefParams]
    geomag: Optional[str]
    surveys: List[models.Survey]
    reference: List[models.Reference]
    sag: Optional[List[Angle]] = None
    bha: Optional[models.BHA]

class ManualCorrectionResult(BaseModel):
    surveys: List[models.ManualCorrectedSurvey]
    stations: List[models.CorrectedStation]

app = APIRouter(
	dependencies=[Depends(get_current_user)]
)
mcorrect_out = convert_out(ManualCorrectionResult)
fcorrect_out = convert_out(Union[models.CorrectionResult, models.ManualCorrectionResult])

def mcorrect_in(pars: ManualCorrectionArgs, conv = Depends(convert_in)) -> dict:
    return conv(pars, CalculationUnitSystem)

@app.post("/mcorrect", 
    tags=["control"],
    summary="Perform manual correction",
    response_model_by_alias=False,
    dependencies=[
        Depends(Authorize(Action.rpc_manual))
    ]
)
async def mcorrect(
        pars: dict = Depends(mcorrect_in), 
        conv = Depends(mcorrect_out)
        ):
    try:
        response = await rpc.post('v1/mcorrect', pars)
    except httpx.ConnectError as ex:
        raise HTTPException(503, 'Computation service is unavaliable')
    except rpc.RPCError:
        raise HTTPException(400, 'RPC error')
    return conv(response.json(), CalculationUnitSystem)


from mwdstdb.tasks.corlv1 import correction_lv1
from mwdstdb.tasks.corlv2 import correction_lv2
from mwdstdb.tasks.corlv3 import correction_lv3


class CorrectionOptions(BaseModel):
    filter: List[bool]
    status_msa: bool
    status_multi: bool
    status_auto: bool
    dni_cs: Optional[models.DniParams]

def process_run(run: dict, opts: CorrectionOptions):
    run['status_multi'] = opts['status_multi']
    run['status_auto'] = opts['status_auto']
    run['status_msa'] = opts['status_msa']
    run['surveys'] = [s for i, s in enumerate(run['surveys']) if opts['filter'][i]]
    run['reference'] = [s for i, s in enumerate(run['reference']) if opts['filter'][i]]
    run['correction'] =  {'dni_cs': opts['dni_cs']} if not opts['status_msa'] else None

def copts_in(pars: CorrectionOptions, conv = Depends(convert_in)) -> dict:
    return conv(pars, CalculationUnitSystem)

@app.post("/fcorrect/{run_id}", 
    tags=["control"],
    summary="Perform run correction with specified manual survey filter",
    response_model_by_alias=False,
    dependencies=[
        Depends(Authorize(Action.rpc_multi))
    ]
)
async def fcorrect(
        run_id: str, 
        opts = Depends(copts_in), 
        db = Depends(DBEngine.get_db), 
        conv = Depends(fcorrect_out)
        ):
    try:
        try:
            borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
        except:
            raise HTTPException(404)
        bh = await crud.get_borehole(db, borehole_id)
        sl: int = bh['well'].get('service_level', 1)
        if sl == 3:
            rq, _, _ = await correction_lv3(db, borehole_id, False)
        elif sl == 2:
            rq, _, _ = await correction_lv2(db, borehole_id, False)
        else:
            rq, _, _ = await correction_lv1(db, borehole_id, False)
        process_run(rq['runs'][-1], opts)
        response = await rpc.post(f'v1/lv{sl}b', rq)

    except httpx.ConnectError as ex:
        raise HTTPException(503, 'Computation service is unavaliable')
    except rpc.RPCError:
        raise HTTPException(400, 'RPC error')

    return conv(response.json()['corrections'][-1], CalculationUnitSystem)

from .core import calc_run, start_task
from bson.objectid import ObjectId


@app.post("/runopts/{run_id}", 
    tags=["control"],
    summary="Perform run correction with specified manual survey filter",
    response_model_by_alias=False,
    dependencies=[
        Depends(Authorize(Action.run_correction))
    ]
)
async def set_opts(
        run_id: str, 
        opts = Depends(copts_in), 
        db = Depends(DBEngine.get_db), 
        dbc = Depends(DBEngine.get_client), 
        ):
    try:
        run_id = ObjectId(run_id)
        async with await dbc.start_session() as s:
            async with s.start_transaction():
                borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
                await crud.update_object(db, models.Run, run_id, {
                    'status_msa': opts['status_msa'], 
                    'status_auto': opts['status_auto'],
                    'status_multi': opts['status_multi'],
                    }, session=s)
                surveys = await crud.get_child_objects(db, models.Survey, run_id, session=s)
                for su, flt in zip(surveys, opts['filter']):
                    await crud.update_object(db, models.Survey, su['_id'], {'visible': flt}, session=s)
                if not opts['status_msa']:
                    await crud.find_and_update_object(db, models.CorrectionGet, {'parent_id': run_id, 'etag': 'manual'}, 
                        {
                            'parent_id': run_id,
                            'etag': 'manual',
                            'result': None,
                            'result_raw': {'dni_cs': opts['dni_cs']},
                        }, 
                        upsert=True, session=s)
                    pass
    except (InvalidId, KeyError):
        raise HTTPException(404)

    task_id = await start_task(db, borehole_id, 'correction', False)
    await calc_run(db, run_id, task_id)
    return