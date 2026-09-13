from app.models import TaskCreate


def validate_task_title(task: TaskCreate) -> str:
    title = task.title.strip()

    if len(title) < 3:
        raise ValueError("Task title must contain at least 3 characters.")

    return title


def validate_task_description(task: TaskCreate) -> str:
    return task.description.strip()