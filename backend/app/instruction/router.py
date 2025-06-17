from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
import os

router = APIRouter()

INSTRUCTION_DIR = os.path.dirname(os.path.abspath(__file__))

@router.get("/instruction/example_train.xlsx")
def download_example_train():
    file_path = os.path.join(INSTRUCTION_DIR, "iris.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл примера для обучения не найден")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="example_train.xlsx",
        headers={"Content-Disposition": "attachment; filename=example_train.xlsx"}
    )

@router.get("/instruction/example_predict.xlsx")
def download_example_predict():
    file_path = os.path.join(INSTRUCTION_DIR, "test_iris.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл примера для прогноза не найден")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="example_predict.xlsx",
        headers={"Content-Disposition": "attachment; filename=example_predict.xlsx"}
    )
