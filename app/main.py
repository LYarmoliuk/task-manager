from fastapi import FastAPI, HTTPException

from app.models import Task, TaskCreate, TaskStatus
from app.services import TaskService
from app.dependency import (
    get_dependency_with_resilience,
    request_dependency,
)


app = FastAPI(
    title="Task Manager API",
    version="1.0.0",
)

task_service = TaskService()

TASK_NOT_FOUND = "Task not found."


@app.get("/tasks")
def get_tasks() -> list[Task]:
    return task_service.get_all_tasks()


@app.get(
    "/tasks/{task_id}",
    responses={404: {"description": "Task not found"}},
)
def get_task(task_id: int) -> Task:
    task = task_service.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail=TASK_NOT_FOUND)

    return task


@app.post(
    "/tasks",
    status_code=201,
    responses={400: {"description": "Invalid task data"}},
)
def create_task(task_data: TaskCreate) -> Task:
    try:
        return task_service.create_task(task_data)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.patch(
    "/tasks/{task_id}/status",
    responses={404: {"description": "Task not found"}},
)
def update_task_status(task_id: int, status: TaskStatus) -> Task:
    task = task_service.update_status(task_id, status)

    if task is None:
        raise HTTPException(status_code=404, detail=TASK_NOT_FOUND)

    return task


@app.delete(
    "/tasks/{task_id}",
    responses={404: {"description": "Task not found"}},
)
def delete_task(task_id: int) -> dict[str, str]:
    deleted = task_service.delete_task(task_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=TASK_NOT_FOUND)

    return {"message": "Task deleted successfully."}


@app.get("/dependency/raw")
def dependency_raw() -> dict[str, str]:
    return {"status": request_dependency()}


@app.get("/dependency/resilient")
def dependency_resilient() -> dict[str, str | int]:
    return get_dependency_with_resilience()