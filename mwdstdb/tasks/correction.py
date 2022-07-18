from typing import List, Optional, Union
from datetime import datetime
import httpx 

from mwdstdb.database import DBEngine
from mwdstdb import crud
from mwdstdb.models import Task, TaskStatus, CorrectionResult, CorrectionGet, Borehole, ManualCorrectionResult
from mwdstdb.models.units import CalculationUnitSystem, StorageUnitSystem
from mwdstdb.utils import convert_units
from mwdstdb.rpc import post, RPCError

from .app import capp, logger
from .corlv1 import correction_lv1
from .corlv2 import correction_lv2
from .corlv3 import correction_lv3



@capp.task(name='correction.main', bind=True, acks_late=True)
async def correction(self, task_id: str):
    db = DBEngine.get_db()
    task = await crud.get_object(db, Task, task_id)
    parent_id = task['parent_id']

    await crud.update_object(db, Task, task_id, {'status': TaskStatus.running, 'started': datetime.utcnow()})

    try:
        await correct_borehole(db, parent_id, task_id)
        await crud.update_object(db, Task, task_id, {'status': TaskStatus.completed, 'finished': datetime.utcnow()})   
    
    except httpx.ConnectError as ex:
        try:
            raise self.retry(exc=ex, countdown=10)
        except httpx.ConnectError:
            logger.info("Can't connect to computation server")
            await crud.update_object(db, Task, task_id, {'status': TaskStatus.faulted, 'finished': datetime.utcnow()})
            return
    except RPCError as ex:
        logger.info("RPC error")
        await crud.update_object(db, Task, task_id, {'status': TaskStatus.faulted, 'finished': datetime.utcnow()})
        return
    except Exception as e:
        logger.info("Unexpected error")
        logger.error(e)
        await crud.update_object(db, Task, task_id, {'status': TaskStatus.faulted, 'finished': datetime.utcnow()})
        return

async def correct_borehole(db, borehole_id, task_id):
    bh: dict = await crud.get_borehole(db, borehole_id)
    etags = [r['etag'] for r in bh['runs']]
    sl: int = bh['well'].get('service_level', 1)
    if sl == 3:
        rq, cids, rids = await correction_lv3(db, borehole_id)
    elif sl == 2:
        rq, cids, rids = await correction_lv2(db, borehole_id)
    else:
        rq, cids, rids = await correction_lv1(db, borehole_id)

    await crud.update_object(db, Task, task_id, {'request': rq})
    response = await post(f'v1/lv{sl}b', rq)

    logger.info('Got OK response')

    jsn = response.json()
    res = convert_units(
        List[Optional[Union[CorrectionResult, ManualCorrectionResult]]], 
        jsn['corrections'],
        CalculationUnitSystem, StorageUnitSystem
        )
        
    for i, (cid, rid) in enumerate(zip(cids, rids)):
        if cid is None:
            await crud.create_object(db, CorrectionGet, {
                'parent_id': rid,
                'etag': etags[i],
                'result': res[i],
                'result_raw': jsn['corrections'][i],
            })
        else:
            await crud.update_object(db, CorrectionGet, cid, 
            {
                'result': res[i],
                'result_raw': jsn['corrections'][i],
            })
    await crud.update_object(db, Borehole, borehole_id, {'links': jsn.get('links')})
    logger.info('DB updated')

