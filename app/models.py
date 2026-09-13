from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(default="", max_length=500)
    priority: TaskPriority = TaskPriority.MEDIUM


class Task(BaseModel):
    id: int
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.TODO