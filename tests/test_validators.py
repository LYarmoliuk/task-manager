import pytest

from app.models import TaskCreate
from app.validators import (
    validate_task_description,
    validate_task_title,
)


def test_validate_title_removes_extra_spaces() -> None:
    task = TaskCreate(title="   Important task   ")

    assert validate_task_title(task) == "Important task"


def test_validate_description_removes_extra_spaces() -> None:
    task = TaskCreate(
        title="Test task",
        description="   Some description   ",
    )

    assert validate_task_description(task) == "Some description"


def test_validate_title_rejects_short_title() -> None:
    with pytest.raises(ValueError):
        TaskCreate(title="Hi")