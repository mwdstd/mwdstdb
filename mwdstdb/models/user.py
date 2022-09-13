from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, validator

from .dbmodel import DBModelMixin, ObjectIdStr
from .units import StorageUnitSystem


class Role(str, Enum):
    SU = 'su'
    DE = 'de'
    FE = 'fe'
    CR = 'cr'


class UserBase(BaseModel):
    _coll = 'users'
    name: str
    login: str
    us: dict = { **StorageUnitSystem, 'ratio_fine': 'ppm' }


class UserCreate(UserBase):
    password: str


class UserPermissions(BaseModel):
    role: Optional[Role]
    oilfields: Optional[List[ObjectIdStr]] = []
    well: Optional[ObjectIdStr]
    client: Optional[ObjectIdStr]


class User(UserBase, UserPermissions, DBModelMixin):
    pass
