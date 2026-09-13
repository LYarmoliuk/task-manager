from app.models import Task, TaskCreate, TaskStatus
from app.validators import validate_task_description, validate_task_title


class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def create_task(self, task_data: TaskCreate) -> Task:
        title = validate_task_title(task_data)
        description = validate_task_description(task_data)

        task = Task(
            id=self._next_id,
            title=title,
            description=description,
            priority=task_data.priority,
        )

        self._tasks[self._next_id] = task
        self._next_id += 1

        return task

    def get_all_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def get_task(self, task_id: int) -> Task | None:
        return self._tasks.get(task_id)

    def update_status(
        self,
        task_id: int,
        status: TaskStatus,
    ) -> Task | None:
        task = self._tasks.get(task_id)

        if task is None:
            return None

        task.status = status
        return task

    def delete_task(self, task_id: int) -> bool:
        if task_id not in self._tasks:
            return False

        del self._tasks[task_id]
        return True