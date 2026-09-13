import pytest

from app.models import TaskCreate, TaskPriority, TaskStatus
from app.services import TaskService


@pytest.fixture
def service() -> TaskService:
    return TaskService()


def test_create_task(service: TaskService) -> None:
    task_data = TaskCreate(
        title="Learn SonarQube",
        description="Prepare laboratory work",
        priority=TaskPriority.HIGH,
    )

    task = service.create_task(task_data)

    assert task.id == 1
    assert task.title == "Learn SonarQube"
    assert task.priority == TaskPriority.HIGH
    assert task.status == TaskStatus.TODO


def test_get_task_returns_none_for_unknown_id(
    service: TaskService,
) -> None:
    assert service.get_task(999) is None


def test_update_task_status(service: TaskService) -> None:
    task = service.create_task(
        TaskCreate(title="Test task")
    )

    updated_task = service.update_status(
        task.id,
        TaskStatus.DONE,
    )

    assert updated_task is not None
    assert updated_task.status == TaskStatus.DONE


def test_delete_task(service: TaskService) -> None:
    task = service.create_task(
        TaskCreate(title="Temporary task")
    )

    assert service.delete_task(task.id) is True
    assert service.get_task(task.id) is None


def test_delete_unknown_task_returns_false(
    service: TaskService,
) -> None:
    assert service.delete_task(999) is False