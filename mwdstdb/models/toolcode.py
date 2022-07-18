from enum import Enum
from typing import Dict
from pydantic import BaseModel


class PropagationMode(str, Enum):
    R = 'R'
    S = 'S'
    G = 'G'

class ErrorTerm(BaseModel):
    wfunc: str
    value: float
    mode: PropagationMode

class ToolcodeInfo(BaseModel):
    _coll = 'toolcodes'
    name: str

class Toolcode(ToolcodeInfo):
    terms: Dict[str, ErrorTerm]

