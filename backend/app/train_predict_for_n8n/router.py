import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import io
import os
import uuid
import logging
from typing import Optional, List, Dict

from training.model import TrainingParameters
from train_prediciton_save.router import run_training_prediction_async
from sessions.utils import (
    create_session_directory,
    get_model_path,
    training_sessions
)

router = APIRouter()

class TrainPredictRequest(BaseModel):
    train_file_base64: str
    predict_file_base64: str
    target_column: Optional[str] = None
    training_time_limit: Optional[int] = None
    problem_type: Optional[str] = None
    evaluation_metric: Optional[str] = None
    training_params: Optional[TrainingParameters] = None

class TrainPredictResponse(BaseModel):
    files: List[Dict[str, str]]
    session_id: str

def get_default_training_params() -> TrainingParameters:
    """Возвращает параметры обучения по умолчанию, как на фронтенде"""
    return TrainingParameters(
        target_column="iris",  # По умолчанию, должно быть передано в запросе
        problem_type=None,
        evaluation_metric=None,
        autogluon_preset="medium_quality",
        models_to_train=["*"],
        fill_missing_method="mean",
        training_time_limit=30
    )

@router.post("/train_predict_base64/", response_model=TrainPredictResponse)
async def train_predict_base64(request: TrainPredictRequest):
    """
    Эндпоинт для обучения модели и прогноза по Excel файлам в формате base64.
    
    1. Получает файлы в base64
    2. Запускает обучение
    3. Делает прогноз
    4. Возвращает файл с прогнозом в base64
    """
    session_id = str(uuid.uuid4())
    
    try:
        logging.info(f"[train_predict_base64] Начало обработки для session_id={session_id}")
        
        # Используем параметры по умолчанию, если не переданы
        training_params = get_default_training_params()

        # Переопределяем параметры из запроса, если они переданы
        if request.target_column:
            training_params.target_column = request.target_column
        if request.training_time_limit is not None:
            training_params.training_time_limit = request.training_time_limit
        if request.problem_type:
            training_params.problem_type = request.problem_type
        if request.evaluation_metric:
            training_params.evaluation_metric = request.evaluation_metric
        
        # Декодируем base64 файлы
        try:
            train_file_bytes = base64.b64decode(request.train_file_base64)
            predict_file_bytes = base64.b64decode(request.predict_file_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка декодирования base64: {str(e)}")
        
        # Загружаем данные для обучения
        try:
            df_train = pd.read_excel(io.BytesIO(train_file_bytes))
            df_predict = pd.read_excel(io.BytesIO(predict_file_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка чтения Excel файлов: {str(e)}")
        
        logging.info(f"[train_predict_base64] Файлы загружены. Train shape: {df_train.shape}, Predict shape: {df_predict.shape}")
        
        # Создаем сессию
        session_path = create_session_directory(session_id)
        
        # Сохраняем файл для прогноза в сессии (используем префикс test_ для совместимости)
        predict_file_path = os.path.join(session_path, f"test_{session_id}.xlsx")
        df_predict.to_excel(predict_file_path, index=False)
        
        # Инициализируем статус сессии
        training_sessions[session_id] = {
            "status": "initializing",
            "session_id": session_id,
            "session_path": session_path,
            "predict_file_path": predict_file_path
        }
        
        # Запускаем обучение и прогноз синхронно (без background task)
        await run_training_prediction_async(
            session_id=session_id,
            df_train=df_train,
            training_params=training_params,
            original_filename="train_file.xlsx",
            token=None  # Для этого эндпоинта не требуется токен
        )
        
        # Проверяем статус выполнения
        session_status = training_sessions.get(session_id, {})
        if session_status.get("status") != "completed":
            error_msg = session_status.get("error", "Неизвестная ошибка обучения")
            raise HTTPException(status_code=500, detail=f"Ошибка обучения: {error_msg}")
        
        # Получаем файл с прогнозом
        prediction_file_path = session_status.get("prediction_file")
        if not prediction_file_path or not os.path.exists(prediction_file_path):
            raise HTTPException(status_code=500, detail="Файл с прогнозом не найден")
        
        # Загружаем прогноз и конвертируем в Excel
        prediction_df = pd.read_parquet(prediction_file_path)
        
        # Конвертируем в Excel в памяти
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            prediction_df.to_excel(writer, index=False, sheet_name='Predictions')
        
        # Кодируем в base64
        output_buffer.seek(0)
        prediction_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        logging.info(f"[train_predict_base64] Успешно завершено для session_id={session_id}")
        
        return TrainPredictResponse(
            files=[{
                "name": f"prediction_{session_id}.xlsx",
                "content": prediction_base64
            }],
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[train_predict_base64] Ошибка для session_id={session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")