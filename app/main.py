from fastapi import FastAPI, HTTPException

from app.models import Task, TaskCreate, TaskStatus
from app.services import TaskService

app = FastAPI(
    title="Task Manager API",
    version="1.0.0",
)

task_service = TaskService()


@app.get("/tasks", response_model=list[Task])
def get_tasks() -> list[Task]:
    return task_service.get_all_tasks()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    task = task_service.get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    return task


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task_data: TaskCreate) -> Task:
    try:
        return task_service.create_task(task_data)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@app.patch("/tasks/{task_id}/status", response_model=Task)
def update_task_status(task_id: int, status: TaskStatus) -> Task:
    task = task_service.update_status(task_id, status)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    deleted = task_service.delete_task(task_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found.")

    return {"message": "Task deleted successfully."}