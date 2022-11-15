from enum import Enum
from bson.objectid import ObjectId
from fastapi import Depends, HTTPException, Request
import fastapi

from mwdstdb import crud
from mwdstdb import models
from mwdstdb.database import DBEngine
from mwdstdb.models import User, Role
from .auth import get_current_user
from .utils import get_resource_id

class Action(str, Enum):
    client_create = 'client:create'
    client_read = 'client:read'
    client_write = 'client:write'
    client_delete = 'client:delete'
    oilfield_create = 'oilfield:create'
    oilfield_read = 'oilfield:read'
    oilfield_write = 'oilfield:write'
    oilfield_delete = 'oilfield:delete'
    pad_create = 'pad:create'
    pad_read = 'pad:read'
    pad_write = 'pad:write'
    pad_delete = 'pad:delete'
    well_create = 'well:create'
    well_read = 'well:read'
    well_write = 'well:write'
    well_delete = 'well:delete'
    well_maintenance = 'well:maintenance'
    borehole_create = 'borehole:create'
    borehole_read = 'borehole:read'
    borehole_write = 'borehole:write'
    borehole_delete = 'borehole:delete'
    run_create = 'run:create'
    run_read = 'run:read'
    run_write = 'run:write'
    run_delete = 'run:delete'
    survey_create = 'survey:create'
    survey_read = 'survey:read'
    survey_write = 'survey:write'
    survey_delete = 'survey:delete'
    survey_import = 'survey:import'
    workflow = 'workflow'
    workflow_default = 'workflow:default'
    workflow_rollback = 'workflow:rollback'
    rpc_manual = 'rpc:manual'
    rpc_multi = 'rpc:multi'
    run_correction = 'run:correction'


async def authorize(user: User, action: Action, res_id, db):
    if user.role == Role.SU: return True

    res_id = ObjectId(res_id)
    if user.role == Role.CR:
        if action in [Action.client_read]:
            if res_id == user.client: return True
        if action in [Action.oilfield_read]:
            cl_id = await crud.get_object_field(db, models.Oilfield, res_id, 'parent_id')
            if cl_id == user.client: return True
        if action in [Action.pad_read]:
            of_id = await crud.get_object_field(db, models.Pad, res_id, 'parent_id')
            cl_id = await crud.get_object_field(db, models.Oilfield, of_id, 'parent_id')
            if cl_id == user.client: return True
        if action in [Action.well_read]:
            pad_id = await crud.get_object_field(db, models.Well, res_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            cl_id = await crud.get_object_field(db, models.Oilfield, of_id, 'parent_id')
            if cl_id == user.client: return True
        if action in [Action.borehole_read]:
            well_id = await crud.get_object_field(db, models.Borehole, res_id, 'parent_id')
            pad_id = await crud.get_object_field(db, models.Well, well_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            cl_id = await crud.get_object_field(db, models.Oilfield, of_id, 'parent_id')
            if cl_id == user.client: return True
        if action in [Action.run_read]:
            bh_id = await crud.get_object_field(db, models.Run, res_id, 'parent_id')
            well_id = await crud.get_object_field(db, models.Borehole, bh_id, 'parent_id')
            pad_id = await crud.get_object_field(db, models.Well, well_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            cl_id = await crud.get_object_field(db, models.Oilfield, of_id, 'parent_id')
            if cl_id == user.client: return True
    
    if user.role == Role.DE:
        if action in [Action.rpc_manual]:
            return True
        if action in [Action.oilfield_read, Action.pad_create]:
            if res_id in user.oilfields: return True
        if action in [Action.pad_read, Action.pad_write, Action.pad_delete, Action.well_create]:
            of_id = await crud.get_object_field(db, models.Pad, res_id, 'parent_id')
            if of_id in user.oilfields: return True
        if action in [Action.well_read, Action.well_write, Action.well_delete, Action.borehole_create, Action.workflow, Action.well_maintenance]:
            pad_id = await crud.get_object_field(db, models.Well, res_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            if of_id in user.oilfields: return True
        if action in [Action.borehole_read, Action.borehole_write, Action.borehole_delete, Action.run_create]:
            well_id = await crud.get_object_field(db, models.Borehole, res_id, 'parent_id')
            pad_id = await crud.get_object_field(db, models.Well, well_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            if of_id in user.oilfields: return True
        if action in [Action.run_read, Action.run_write, Action.run_delete, 
                Action.rpc_multi, Action.run_correction, Action.survey_create, Action.survey_import]:
            bh_id = await crud.get_object_field(db, models.Run, res_id, 'parent_id')
            well_id = await crud.get_object_field(db, models.Borehole, bh_id, 'parent_id')
            pad_id = await crud.get_object_field(db, models.Well, well_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            if of_id in user.oilfields: return True
        if action in [Action.survey_read, Action.survey_write, Action.survey_delete, Action.workflow_rollback]:
            run_id = await crud.get_object_field(db, models.Survey, res_id, 'parent_id')
            bh_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
            well_id = await crud.get_object_field(db, models.Borehole, bh_id, 'parent_id')
            pad_id = await crud.get_object_field(db, models.Well, well_id, 'parent_id')
            of_id = await crud.get_object_field(db, models.Pad, pad_id, 'parent_id')
            if of_id in user.oilfields: return True

    if user.role == Role.FE:
        if action in [Action.rpc_manual, Action.workflow_default]:
            return True
        if action in [Action.well_read, Action.workflow]:
            if res_id == user.well: return True
        if action in [Action.borehole_read]:
            well_id = await crud.get_object_field(db, models.Borehole, res_id, 'parent_id')
            if well_id == user.well: return True
        if action in [Action.run_read]:
            bh_id = await crud.get_object_field(db, models.Run, res_id, 'parent_id')
            well_id = await crud.get_object_field(db, models.Borehole, bh_id, 'parent_id')
            if well_id == user.well: return True
        if action in [Action.survey_read, Action.workflow_rollback]:
            run_id = await crud.get_object_field(db, models.Survey, res_id, 'parent_id')
            bh_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
            well_id = await crud.get_object_field(db, models.Borehole, bh_id, 'parent_id')
            if well_id == user.well: return True
        pass

    return False


class Authorize:
    def __init__(self, action: Action, throw_exception: bool = True):
        self.action = action
        self.throw_exception = throw_exception

    async def __call__(self, user: User = Depends(get_current_user), res_id: str = Depends(get_resource_id), db =  Depends(DBEngine.get_db)):
        res = await authorize(user, self.action, res_id, db)
        if not res and self.throw_exception:
            raise HTTPException(status_code=403, detail="Access denied")
        return res

