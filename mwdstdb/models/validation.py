from typing import List, Optional
from pydantic import BaseModel, Field, validator, root_validator

from .bha import BhaElementType, Material, BhaElement, Blade

class ValCiStation(BaseModel):
	md: float
	inc: float = Field(..., ge=0., le = 180.)

class ValStation(ValCiStation):
	az: float = Field(..., ge=0., lt=360.)

class ValSurvey(BaseModel):
	md: float

class ValCi(BaseModel):
    __root__: List[ValCiStation] = []

    @validator('__root__')
    def check_sorted_mds(cls, v: List[ValCiStation]):
        mds = [s.md for s in v]
        if any((s1 > s2 for s1, s2 in zip(mds[:-1], mds[1:]))):
            raise ValueError("Continous inclination depth is not consistient: Not sorted by MD")
        return v
    
    @validator('__root__')
    def check_unique_mds(cls, v):
        v_sorted = sorted(v, key=lambda s: s.md)
        if any((s1.md == s2.md for s1, s2 in zip(v_sorted[:-1], v_sorted[1:]))):
            raise ValueError("Continous inclination depth is not consistient: Repeat of the same depth")
        return v

class ValBhaElement(BaseModel):
    type: BhaElementType
    od: float
    id: float = Field(..., gt = 0.)
    weight: float = Field(..., gt = 0.)
    length: float = Field(..., gt = 0.)
    material: Material

    @root_validator
    def check_id_lt_od(cls, values):
        od, id = values.get('od'), values.get('id')
        if od is not None and id is not None and od <= id:
            raise ValueError('id must be less than od')
        return values
    
    @root_validator
    def check_mwd_is_nonmag(cls, values):
        mag_mats = [Material.chrome_alloy, Material.steel_alloy, Material.steel]
        type, material = values.get('type'), values.get('material')
        if type is not None and material is not None and \
            type == BhaElementType.mwd and material in mag_mats:
            raise ValueError('Magnetic MWD')
        return values

class ValBlade(BaseModel):
    od: float = Field(..., gt = 0.)
    center_to_bit: float
    length: float = Field(..., gt = 0.)

class ValBHA(BaseModel):
    structure: List[ValBhaElement]
    blades: List[ValBlade]
    tf_correction: float = 0. #SL >= 2 BHA has motor
    bend_angle: float = Field(default = 0., ge = 0., le = 4.) #if no bend elements present
    bend_to_bit: float = 0. #if no bend elements present
    dni_to_bit: float = 0. #if no MWD element present
    
    @validator('structure')
    def check_bit_is_first(cls, structure: List[ValBhaElement]):
        bit_element_idxs = [i for i, el in enumerate(structure) if el.type == BhaElementType.bit]
        if len(bit_element_idxs) > 1:
            raise ValueError('There is can be the only one bit')
        if len(bit_element_idxs) == 1 and bit_element_idxs[0] != 0:
            raise ValueError('The bit is not the first element')
        return structure

    @root_validator
    def check_dni2bit(cls, values: dict):
        structure, dni_to_bit = values.get('structure'), values.get('dni_to_bit')
        if structure is not None:
            mwd_element_idxs = [i for i, el in enumerate(structure) if el.type == BhaElementType.mwd]
            if len(mwd_element_idxs) > 1:
                raise ValueError('Only one MWD is supported')
            if len(mwd_element_idxs) == 1:
                idx = mwd_element_idxs[0]
                if dni_to_bit is None:
                    raise ValueError('dni_to_bit is required if MWD present')
                cumlen = 0
                for i in range(0, idx):
                    cumlen += structure[i].length
                if dni_to_bit < cumlen or dni_to_bit > cumlen + structure[idx].length:
                    raise ValueError('dni_to_bit is not within MWD')
        return values
    
    @root_validator
    def check_bitsize_gt_ods(cls, values: dict):
        structure: List[ValBhaElement] = values.get('structure')
        blades: List[ValBlade] = values.get('blades')
        
        if structure is not None and blades is not None:
            bit_elements = [el for el in structure if el.type == BhaElementType.bit]
            if len(bit_elements) == 1:
                bit = bit_elements[0]
                if any(el.od > bit.od for el in structure) or \
                    any(el.od > bit.od for el in blades):
                    raise ValueError('Bit OD is not maximum among elements')

        return values

    @root_validator
    def check_blades_od_gt_element_od(cls, values: dict):
        structure: List[BhaElement] = values.get('structure')
        blades: List[Blade] = values.get('blades')
        
        if structure is not None and blades is not None:
            cumlen = [0]
            for el in structure:
                cumlen += [cumlen[-1] + el.length]
            for bl in blades:
                idx = [i for (i, l) in enumerate(cumlen) if (cumlen[i-1] < bl.center_to_bit <= l)]
                if len(idx) != 1:
                    raise ValueError('Cannot find bladed tubular')
                idx = idx[0] - 1
                if structure[idx].od >= bl.od:
                    raise ValueError('Blade OD is less than tubular')

        return values

class Run1(BaseModel):
    surveys: List[ValSurvey]

class Run2(Run1):
    bha: ValBHA
    mud_weight: float

class Run3(Run2):
    ci: Optional[ValCi]

class Validator1(BaseModel):
    runs: List[Run1]

class Validator2(BaseModel):
    runs: List[Run2]

class Validator3(BaseModel):
    runs: List[Run3]

from bson.objectid import ObjectId

def validate_ci(cis: list):
    ValCi.parse_obj(cis)

async def validate_borehole(db, borehole_id, **kwargs):
    pipeline = [
        {'$match' : { '_id' : ObjectId(borehole_id)}},
        {'$lookup': {'from': 'wells', 'localField': 'parent_id', 'foreignField': '_id', 'as': 'well'}},
        {'$unwind': {'path': '$well'}},
        {'$lookup': {'from': 'runs', 
            'let': {'borehole_id': '$_id'}, 
            'pipeline': [
                {'$match': {'$expr': {'$eq': ['$parent_id', '$$borehole_id']}}}, 
                {'$lookup': {
                    'from': 'surveys', 
                    'let': {'parent_id': '$_id'}, 
                    'pipeline': [
                        {'$match': {'$expr': {'$eq': ['$$parent_id', '$parent_id']}}}, 
                        {'$sort': {'_id': 1}}
                    ], 
                    'as': 'surveys'
                }},
                {'$lookup': {'from': 'ci', 'localField': 'ci_id', 'foreignField': '_id', 'as': 'ci'}}, 
                {'$unwind': {'path': '$ci', 'preserveNullAndEmptyArrays': True}}, 
                {'$set': {'ci': '$ci.stations'}},
                {'$sort': {'_id': 1}}            
            ],
            'as': 'runs'}},
    ]
    bh = (await db['boreholes'].aggregate(pipeline, **kwargs).to_list(1))[0]
    sl = bh['well'].get('service_level', 1)
    if sl == 1:
        Validator1.parse_obj(bh)
    elif sl == 2:
        Validator2.parse_obj(bh)
    elif sl == 3:
        Validator3.parse_obj(bh)
       




