from fastapi import APIRouter, Depends

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from .core import ensure_manual_mode, calc_run
from .deps.auth import get_current_user
from .deps.units import convert_out, survey_in
from .deps.actrl import Action, Authorize
from .deps import exists


app = APIRouter(
	dependencies=[
        Depends(get_current_user),
        Depends(exists.survey)
        ]
)

survey_out = convert_out(models.SurveyGet)

@app.get("/{survey_id}", 
    tags=["surveys"],
    summary="Get survey information",
    response_model_by_alias=False,
    dependencies=[Depends(Authorize(Action.survey_read))]
)
async def get_survey(
        survey_id: str, 
        db = Depends(DBEngine.get_db), 
        conv = Depends(survey_out), 
        ):
    r = await crud.get_survey(db, survey_id)
    return conv(r)


@app.put("/{survey_id}", 
    tags=["surveys"],
    summary="Update survey information",
    dependencies=[Depends(Authorize(Action.survey_write))]
)
async def update_survey(
        survey_id: str, 
        d: dict = Depends(survey_in), 
        db = Depends(DBEngine.get_db), 
        ):
    run_id = await crud.get_object_field(db, models.Survey, survey_id, 'parent_id')
    borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
    well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
    await ensure_manual_mode(db, well_id)
    await crud.update_object(db, models.Survey, survey_id, d)
    run_id = await crud.get_object_field(db, models.Survey, survey_id, 'parent_id')
    await calc_run(db, str(run_id))


@app.delete("/{survey_id}", 
    tags=["surveys"],
    summary="Delete survey",
    dependencies=[Depends(Authorize(Action.survey_delete))]
)
async def delete_survey(
        survey_id: str, 
        db = Depends(DBEngine.get_db), 
        ):
    run_id = await crud.get_object_field(db, models.Survey, survey_id, 'parent_id')
    borehole_id = await crud.get_object_field(db, models.Run, run_id, 'parent_id')
    well_id = await crud.get_object_field(db, models.Borehole, borehole_id, 'parent_id')
    await ensure_manual_mode(db, well_id)
    await crud.delete_object(db, models.Survey, survey_id)

    await calc_run(db, str(run_id))


