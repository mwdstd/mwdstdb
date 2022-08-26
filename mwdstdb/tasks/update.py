from typing import List, Optional
from datetime import datetime, timezone
from math import acos, asin, atan2, pi, sin, sqrt, degrees, radians
import numpy as np
from bson.objectid import ObjectId
from pydantic import BaseModel
import httpx 
from celery import group

from mwdstdb import crud, models
from mwdstdb.database import DBEngine
from mwdstdb.utils import convert_units
from mwdstdb.models.units import Angle, Length, CalculationUnitSystem, StorageUnitSystem
from mwdstdb.rpc import post
from .app import capp
from .correction import correction


@capp.task(name='update.well', bind=True, acks_late=True)
async def update_calc_fields_well(self, well_id):
    db = DBEngine.get_db()
    well = await crud.get_well(db, well_id)

    g = well['grav_value'] if well['grav'] == models.GravityModel.manual else gravity(well['lat'])
    
    if well['north_type'] == models.NorthType.true:
        grid = 0.
    elif well['grid'] == models.GridModel.manual:
        grid = well['grid_value']
    else:
        try:
            #request grid
            response = await post('v1/refcalc', {
                'latitude': radians(well['lat']), 'longitude': radians(well['lon']),
                'altitude': 0.,
                'date': datetime.now(timezone.utc).isoformat(),
                'gmag_mod': 'WMM2020',
                'crustal_field': False,
                'north_type': well['north_type']}
            )
            jsn = response.json()
            grid = degrees(jsn['base_point']['grid'])
        except httpx.ConnectError as ex:
            self.retry(exc=ex, countdown=10)
            return


    await crud.update_object(db, models.Well, well_id, {'grav_value': g, 'grid_value': grid})

    group([update_calc_fields_borehole.s(str(borehole['_id'])) for borehole in well['boreholes']]).apply_async(countdown=0)

class GeoRequest(BaseModel):
    latitude: Angle
    longitude: Angle
    altitude: Length
    date: datetime
    gmag_mod: str
    crustal_field: bool
    north_type: models.NorthType
    plan: Optional[List[models.Station]] = None

class GeoResponse(BaseModel):
    base_point: models.MagRef
    points: Optional[List[models.MagRefPoint]]

@capp.task(name='update.borehole', bind=True, acks_late=True)
async def update_calc_fields_borehole(self, borehole_id):
    db = DBEngine.get_db()
    borehole = await crud.get_borehole(db, borehole_id)
    well = borehole['well']
    ref = None
    try:
        if well['geomag'] == models.GeomagModel.wmm:
            rq = {
                'latitude': well['lat'], 
                'longitude': well['lon'],
                'altitude': well['alt'] + borehole['rkb_elevation'],
                'date': borehole['start_date'],
                'gmag_mod': 'WMM2020',
                'crustal_field': True,
                'north_type': well['north_type'],
            }
            rq = convert_units(GeoRequest, rq, StorageUnitSystem, CalculationUnitSystem)
            response = await post('v1/refcalc', rq)
            res = response.json()
            res = convert_units(GeoResponse, res, CalculationUnitSystem, StorageUnitSystem)
            ref = res['base_point']
        elif well['geomag'] == models.GeomagModel.emm:
            rq = {
                'latitude': well['lat'], 
                'longitude': well['lon'],
                'altitude': well['alt'] + borehole['rkb_elevation'],
                'date': borehole['start_date'],
                'gmag_mod': 'EMM2017',
                'crustal_field': True,
                'north_type': well['north_type'],
            }
            rq = convert_units(GeoRequest, rq, StorageUnitSystem, CalculationUnitSystem)
            response = await post('v1/refcalc', rq)
            res = response.json()
            res = convert_units(GeoResponse, res, CalculationUnitSystem, StorageUnitSystem)
            ref = res['base_point']
    except httpx.ConnectError as ex:
        self.retry(exc=ex, countdown=10)
        return

    changes = {}

    if ref is not None:
        changes = {**changes, 'ref_head': ref}

    # last depth
    pipeline = [
        {'$match' : { '_id' : ObjectId(borehole_id)}},
        {'$lookup': {'from': 'runs', 'localField': '_id', 'foreignField': 'parent_id', 'as': 'runs'}}, 
        {'$unwind': {'path': '$runs'}}, 
        {'$unwind': {'path': '$runs.slidesheet'}}, 
        {'$group': {'_id': '$_id', 'last_depth': {'$max': '$runs.slidesheet.md_stop'}}}
    ]
    obj = (await db[models.Borehole._coll].aggregate(pipeline).to_list(1))
    if len(obj) > 0:
        changes = {**changes, 'last_depth': obj[0]['last_depth']}

    await crud.update_object(db, models.Borehole, borehole_id, changes)

    group([update_calc_fields_run.s(str(run['_id']), None) for run in borehole['runs']]).apply_async()

@capp.task(name='update.run', bind=True, acks_late=True)
async def update_calc_fields_run(self, run_id: str, correction_task_id: str):
    db = DBEngine.get_db()
    run = await crud.get_run(db, run_id, False)
    well = run['well']
    borehole = run['borehole']

    head_ref = None
    plan_ref = None

    if well['geomag'] == models.GeomagModel.bggm or \
        well['geomag'] == models.GeomagModel.hdgm or \
        well['geomag'] == models.GeomagModel.wmm:
        head_ref = {'g': well['grav_value'], **borehole['ref_head'], 'grid': well['grid_value']}
    elif well['geomag'] == models.GeomagModel.emm:
        try:
            rq = {
                    'latitude': well['lat'], 
                    'longitude': well['lon'],
                    'altitude': well['alt'] + borehole['rkb_elevation'],
                    'date': borehole['start_date'],
                    'gmag_mod': 'EMM2017',
                    'crustal_field': True,
                    'north_type': well['north_type'],
                    'plan': run['plan']['stations'] 
                }
            rq = convert_units(GeoRequest, rq, StorageUnitSystem, CalculationUnitSystem)
            response = await post('v1/refcalc', rq)
            res = response.json()
            res = convert_units(GeoResponse, res, CalculationUnitSystem, StorageUnitSystem)
            plan_ref = res['points']
            if plan_ref is None: 
                head_ref = {'g': well['grav_value'], **borehole['ref_head'], 'grid': well['grid_value']}
        except httpx.ConnectError as ex:
            self.retry(exc=ex, countdown=10)
            return
    else:
        plan_ref = borehole['ref_traj']
    
    if head_ref is not None:
        reference = [head_ref] * len(run['surveys'])
    else:
        hmr = plan_ref[0]
        head_ref = {'g': well['grav_value'], 'b': hmr['b'], 'dip': hmr['dip'], 'dec': hmr['dec'], 'grid': well['grid_value']}
        md = [s['md'] for s in run['surveys']]
        planmd = [s['md'] for s in plan_ref]
        b = [s['b'] for s in plan_ref]
        dec = [s['dec'] for s in plan_ref]
        dip = [s['dip'] for s in plan_ref]
        bs = np.interp(md, planmd, b)
        decs = np.interp(md, planmd, dec)
        dips = np.interp(md, planmd, dip)
        reference = [{'g': well['grav_value'], 'b': b_, 'dip': dip_, 'dec': dec_, 'grid': well['grid_value']} for b_, dip_, dec_ in zip(bs, dips, decs)]

    stations = [{
        'md': s['md'],
        'inc': degrees(acos(s['gz'] / g)),
        'az': degrees((atan2(ew, ns) + (radians(r['dec'] - r['grid'])) + 2 * pi) % (2 * pi)),
        'tf': degrees(atan2(-s['gx'], -s['gy'])),
        'tg': g, 'tb': b, 'dip': degrees(dip)
    } for s, (g, b, dip, ns, ew), r in zip(run['surveys'], (_calc(x) for x in run['surveys']), reference)]

    etag = await crud.compute_etag(db, run_id) if run['status_msa'] else 'manual'
    await crud.update_object(db, models.Run, run_id, {
            'head_ref': head_ref,
            'reference': reference,
            'stations': stations,
            'etag': etag
        })
    
    if correction_task_id is not None:
        correction.apply_async(args=[correction_task_id], countdown = 1)

def gravity(latitude: float) -> float:
    # calculate gravity reference
    lat = radians(latitude)
    total_g = 9.7803253359 * (1 + 0.00193185265241 * sin(lat) ** 2) / sqrt(1 - 0.00669437999013 * sin(lat) ** 2)
    return total_g

def _calc(s):
    g = sqrt(s['gx'] * s['gx'] + s['gy'] * s['gy'] + s['gz'] * s['gz'])
    b = sqrt(s['bx'] * s['bx'] + s['by'] * s['by'] + s['bz'] * s['bz'])
    dip = asin((s['gx'] * s['bx'] + s['gy'] * s['by'] + s['gz'] * s['bz']) / (g * b))
    ew = (s['gx'] * s['by'] - s['gy'] * s['bx']) * g
    ns = s['bz'] * (s['gx'] * s['gx'] + s['gy'] * s['gy']) - s['gz'] * (s['gx'] * s['bx'] + s['gy'] * s['by'])
    return g, b, dip, ns, ew