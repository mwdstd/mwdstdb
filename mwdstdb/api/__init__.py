from fastapi import APIRouter

from .user import app as user_router
from .client import app as client_router
from .oilfield import app as oilfield_router
from .pad import app as pad_router
from .well import app as well_router
from .borehole import app as borehole_router
from .run import app as run_router
from .survey import app as survey_router
from .toolcode import app as toolcode_router
from .tasks import app as task_router
from .workflow import app as workflow_router, rollback_app, wf_def_app
from .export import app as export_router
from .control import app as control_router
from .auth import app as auth_router
from .rpc import app as rpc_router
from .lists import app as lists_router
from .events import app as events_router
from .meta import app as meta_router

router = APIRouter()
router.include_router(user_router, prefix='/users')
router.include_router(client_router, prefix='/clients')
router.include_router(oilfield_router, prefix='/fields')
router.include_router(pad_router, prefix='/pads')
router.include_router(well_router, prefix='/wells')
router.include_router(borehole_router, prefix='/boreholes')
router.include_router(run_router, prefix='/runs')
router.include_router(survey_router, prefix='/surveys')
router.include_router(toolcode_router, prefix='/toolcodes')
router.include_router(task_router, prefix='/tasks')
router.include_router(export_router, prefix='/export')
router.include_router(control_router, prefix='/control')
router.include_router(workflow_router, prefix='/workflow')
router.include_router(wf_def_app, prefix='/workflow')
router.include_router(rollback_app, prefix='/workflow')
router.include_router(auth_router, prefix='/auth')
router.include_router(rpc_router, prefix='/rpc')
router.include_router(lists_router)
router.include_router(events_router, prefix='/events')
router.include_router(meta_router)

