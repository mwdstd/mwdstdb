from datetime import datetime
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel
from .dbmodel import DBModelMixin, ObjectIdStr


class TaskStatus(str, Enum):
    scheduled = 'scheduled'
    running = 'running'
    completed = 'completed'
    canceled = 'canceled'
    faulted = 'faulted'

class TaskType(str, Enum):
    correction = 'correction'

class Task(BaseModel):
    _coll = 'tasks'
    type: TaskType
    status: TaskStatus
    started: Optional[datetime]
    finished: Optional[datetime]

class TaskDb(Task, DBModelMixin):
    parent_id: ObjectIdStr
