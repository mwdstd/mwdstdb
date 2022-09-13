from types import GeneratorType
from typing import Any, Dict, Callable, List, Tuple, Type, Union
from datetime import datetime
from pydantic import BaseModel, parse_obj_as

from .models.units import get_unit_converters
from .models import Survey, ManualCorrectedSurvey, DniParams, DniUnc

sequence_types = (list, tuple, set, frozenset, GeneratorType)

def isoformat(o: datetime) -> str:
    return o.isoformat()


def convert_types(obj: Any, type_converters: Dict[Any, Callable[[Type[Any]], Any]]) -> Any:
    if isinstance(obj, dict):
        return {k: convert_types(v, type_converters) for k, v in obj.items()}
    if isinstance(obj, sequence_types):
        return obj.__class__(convert_types(v, type_converters) for i, v in enumerate(obj))
    for base in obj.__class__.__mro__[:-1]:
        try:
            encoder = type_converters[base]
        except KeyError:
            continue
        return encoder(obj)
    return obj


import numpy as np

class AxOrder(BaseModel):
    gaxes: Tuple[str, str, str]
    maxes: Tuple[str, str, str]
    gaxesi: Tuple[bool, bool, bool]
    maxesi: Tuple[bool, bool, bool]

def ax_ind(mnem: Tuple[str, str, str]):
    return [ord(c.upper()) - ord('X') for c in mnem]

def reorder_axes(s: Union[Survey, ManualCorrectedSurvey, DniParams], ax_from: AxOrder, ax_to: AxOrder):
    fpig = np.array(ax_ind(ax_from.gaxes))
    tpig = np.array(ax_ind(ax_to.gaxes))
    fpim = np.array(ax_ind(ax_from.maxes))
    tpim = np.array(ax_ind(ax_to.maxes))
    finvg = (-1) ** np.array(ax_to.gaxesi)
    tinvg = (-1) ** np.array(ax_from.gaxesi)
    finvm = (-1) ** np.array(ax_to.maxesi)
    tinvm = (-1) ** np.array(ax_from.maxesi)
    if not isinstance(s, DniParams):
        s.gx._value, s.gy._value, s.gz._value = ((np.array([s.gx._value, s.gy._value, s.gz._value])[fpig] * finvg * tinvg)[tpig])
        s.bx._value, s.by._value, s.bz._value = (np.array([s.bx._value, s.by._value, s.bz._value])[fpim] * finvm * tinvm)[tpim]
    else:
        s.ABX._value, s.ABY._value, s.ABZ._value = ((np.array([s.ABX._value, s.ABY._value, s.ABZ._value])[fpig] * finvg * tinvg)[tpig])
        s.ASX._value, s.ASY._value, s.ASZ._value = ((np.array([s.ASX._value, s.ASY._value, s.ASZ._value])[fpig] * finvg * tinvg)[tpig])
        s.MBX._value, s.MBY._value, s.MBZ._value = (np.array([s.MBX._value, s.MBY._value, s.MBZ._value])[fpim] * finvm * tinvm)[tpim]
        s.MSX._value, s.MSY._value, s.MSZ._value = (np.array([s.MSX._value, s.MSY._value, s.MSZ._value])[fpim] * finvm * tinvm)[tpim]
        if isinstance(s, DniUnc):
            s.ABX._value, s.ABY._value, s.ABZ._value = np.abs([s.ABX._value, s.ABY._value, s.ABZ._value])
            s.ASX._value, s.ASY._value, s.ASZ._value = np.abs([s.ASX._value, s.ASY._value, s.ASZ._value])
            s.MBX._value, s.MBY._value, s.MBZ._value = np.abs([s.MBX._value, s.MBY._value, s.MBZ._value])
            s.MSX._value, s.MSY._value, s.MSZ._value = np.abs([s.MSX._value, s.MSY._value, s.MSZ._value])


def reorder_axes_recursively(obj: Any, ax_from: AxOrder, ax_to: AxOrder):
    if isinstance(obj, (Survey, ManualCorrectedSurvey, DniParams)):
        reorder_axes(obj, ax_from, ax_to)
    
    if isinstance(obj, sequence_types):
        for v in obj:
            reorder_axes_recursively(v, ax_from, ax_to)
        return
    if isinstance(obj, BaseModel):
        for _, v in obj:
            reorder_axes_recursively(v, ax_from, ax_to)
    

def convert_units_bm_to_dict(obj: Union[BaseModel, List[BaseModel]], usfrom, usto, encoders: dict = None):
    axfrom = AxOrder.parse_obj(usfrom)
    axto = AxOrder.parse_obj(usto)
    reorder_axes_recursively(obj, axfrom, axto)
    encoders = encoders or {}
    if obj is None:
        return None
    if isinstance(obj, sequence_types):
        res = obj.__class__(v.dict() if v is not None else None for i, v in enumerate(obj))
    else: 
        res = obj.dict()
    return convert_types(res, {**get_unit_converters(usfrom, usto), datetime: isoformat, **encoders})

def convert_units(modelType: Union[Type[BaseModel], Type[List[BaseModel]]], obj: dict, usfrom, usto, encoders: dict = None):
    res = parse_obj_as(modelType, obj)
    return convert_units_bm_to_dict(res, usfrom, usto, encoders)
