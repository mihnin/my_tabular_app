import base64
import json
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
        
        # Загружаем прогноз
        prediction_df = pd.read_parquet(prediction_file_path)
        
        # Создаём Excel с метаинформацией (аналогично prediction/router.py)
        output_buffer = create_excel_with_metadata(prediction_df, session_id)
        
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

def create_excel_with_metadata(prediction_df: pd.DataFrame, session_id: str) -> io.BytesIO:
    """
    Создаёт Excel файл с прогнозом и метаинформацией (leaderboard, параметры обучения, feature importance).
    Аналогично функции download_prediction_file из prediction/router.py
    """
    session_path = training_sessions[session_id]["session_path"]
    leaderboard_path = os.path.join(session_path, "leaderboard.csv")
    metadata_path = os.path.join(session_path, "metadata.json")
    
    # Читаем leaderboard
    df_leaderboard = None
    if os.path.exists(leaderboard_path):
        try:
            df_leaderboard = pd.read_csv(leaderboard_path)
        except Exception as e:
            logging.warning(f"Не удалось прочитать leaderboard: {e}")
            df_leaderboard = None

    # Читаем параметры обучения
    params_dict = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            params_dict = metadata.get("training_parameters", {})
        except Exception as e:
            logging.warning(f"Не удалось прочитать параметры обучения: {e}")
            params_dict = None

    # Формируем новый Excel-файл с несколькими листами
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Первый лист — прогноз
        prediction_df.to_excel(writer, sheet_name="Prediction", index=False)
        
        # Второй лист — leaderboard
        if df_leaderboard is not None:
            df_leaderboard.to_excel(writer, sheet_name="Leaderboard", index=False)
            # Всегда выделяем строку с максимальным score_val зелёным цветом
            try:
                ws = writer.sheets["Leaderboard"]
                if "score_val" in df_leaderboard.columns:
                    best_idx = df_leaderboard["score_val"].idxmax()
                    excel_row = best_idx + 2  # 1-based, +1 for header
                    format_green = writer.book.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
                    ws.set_row(excel_row - 1, None, format_green)
            except Exception as e:
                logging.warning(f"Не удалось выделить лучшую строку в leaderboard: {e}")
        else:
            pd.DataFrame({"info": ["Leaderboard not found"]}).to_excel(writer, sheet_name="Leaderboard", index=False)
        
        # Третий лист — параметры обучения
        if params_dict is not None:
            pd.DataFrame(list(params_dict.items()), columns=["Parameter", "Value"]).to_excel(writer, sheet_name="TrainingParams", index=False)
        else:
            pd.DataFrame({"info": ["Training parameters not found"]}).to_excel(writer, sheet_name="TrainingParams", index=False)
        
        # Четвёртый лист — feature_importance
        fi_path = os.path.join(session_path, "autogluon", "feature_importance.csv")
        feature_importance = None
        if os.path.exists(fi_path):
            try:
                feature_importance = pd.read_csv(fi_path).to_dict(orient="records")
                logging.info(f"Feature importance добавлен для session_id={session_id}")
            except Exception as e:
                logging.warning(f"Не удалось прочитать feature importance: {e}")
        
        if feature_importance and isinstance(feature_importance, list) and len(feature_importance) > 0:
            try:
                df_fi = pd.DataFrame(feature_importance)
                df_fi.to_excel(writer, sheet_name="FeatureImportance", index=False)
            except Exception as e:
                pd.DataFrame({"info": [f"Feature importance error: {e}"]}).to_excel(writer, sheet_name="FeatureImportance", index=False)
        else:
            pd.DataFrame({"info": ["Feature importance not found"]}).to_excel(writer, sheet_name="FeatureImportance", index=False)
        
        # Пятый лист — WeightedEnsemble
        weighted_ensemble_path = os.path.join(session_path, "autogluon", "model_metadata.json")
        if os.path.exists(weighted_ensemble_path):
            try:
                with open(weighted_ensemble_path, "r", encoding="utf-8") as f:
                    model_metadata = json.load(f)
                # Только WeightedEnsemble_L1_weights и WeightedEnsemble_L2_weights
                ensemble_keys = [k for k in ("WeightedEnsemble_L1_weights", "WeightedEnsemble_L2_weights") if k in model_metadata]
                if ensemble_keys:
                    ws = writer.book.add_worksheet("WeightedEnsemble")
                    row = 0
                    for key in ensemble_keys:
                        ws.write(row, 0, key.replace("_weights", ""))
                        row += 1
                        weights = model_metadata[key]
                        if isinstance(weights, dict):
                            ws.write(row, 0, "Model")
                            ws.write(row, 1, "Weight")
                            row += 1
                            for model, weight in weights.items():
                                ws.write(row, 0, f"  {model}")
                                ws.write(row, 1, weight)
                                row += 1
                        else:
                            ws.write(row, 0, "(weights not found or not a dict)")
                            row += 1
                        ws.write(row, 0, "")
                        row += 1
            except Exception as e:
                logging.warning(f"Не удалось добавить WeightedEnsemble: {e}")
    
    output.seek(0)
    return output