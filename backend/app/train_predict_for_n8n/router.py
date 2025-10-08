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

# Импорты для работы с MinIO
from minio import Minio
from minio.error import S3Error

from training.model import TrainingParameters
from train_prediciton_save.router import run_training_prediction_async
from sessions.utils import (
    create_session_directory,
    get_model_path,
    training_sessions
)

router = APIRouter()

# --- Вспомогательные функции для работы с MinIO ---

def get_minio_client() -> Minio:
    """Создает и возвращает клиент MinIO на основе переменных окружения."""
    try:
        minio_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        minio_secure = os.getenv('MINIO_SECURE', '0') == '1'
        return Minio(
            minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=minio_secure
        )
    except Exception as e:
        logging.error(f"Ошибка при создании клиента MinIO: {e}")
        raise HTTPException(status_code=500, detail="Не удалось настроить подключение к MinIO.")

def get_file_from_minio(minio_file_id: str) -> bytes:
    """
    Скачивает файл из MinIO по его ID.
    Формат ID: <bucket_name>/<object_name>
    """
    if '/' not in minio_file_id:
        raise HTTPException(status_code=400, detail='minio_file_id должен быть в формате <bucket>/<object>')
    
    bucket_name, object_name = minio_file_id.split('/', 1)
    client = get_minio_client()
    
    try:
        response = client.get_object(bucket_name, object_name)
        data = response.read()
        return data
    except S3Error as e:
        logging.error(f"Ошибка получения файла из MinIO '{minio_file_id}': {e}")
        raise HTTPException(status_code=404, detail=f"Ошибка получения файла из MinIO: {e}")
    finally:
        if 'response' in locals() and response:
            response.close()
            response.release_conn()

def upload_file_to_minio(file_bytes: bytes, bucket: str, object_name: str, content_type: str):
    """Загружает байты файла в MinIO."""
    client = get_minio_client()
    try:
        # Проверяем, существует ли бакет, и создаем, если нет
        found = client.bucket_exists(bucket)
        if not found:
            client.make_bucket(bucket)
            logging.info(f"Создан бакет: '{bucket}'")

        client.put_object(
            bucket,
            object_name,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type
        )
        logging.info(f"Файл успешно загружен в MinIO: '{bucket}/{object_name}'")
    except S3Error as e:
        logging.error(f"Ошибка загрузки файла в MinIO '{bucket}/{object_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла в MinIO: {e}")

# --- Обновленные Pydantic модели ---

class TrainPredictRequest(BaseModel):
    train_minio_file_id: str  # ID файла для обучения в MinIO
    predict_minio_file_id: str # ID файла для прогноза в MinIO
    target_column: Optional[str] = None
    training_time_limit: Optional[int] = None
    problem_type: Optional[str] = None
    evaluation_metric: Optional[str] = None
    training_params: Optional[TrainingParameters] = None

class FileResponse(BaseModel):
    fileId: str
    fileName: str
    mimeType: str

class TrainPredictResponse(BaseModel):
    files: List[FileResponse]
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
    Эндпоинт для обучения модели и прогноза по Excel файлам из MinIO.
    
    1. Получает ID файлов для обучения и прогноза из MinIO.
    2. Скачивает файлы.
    3. Запускает обучение и делает прогноз.
    4. Формирует итоговый Excel-файл с прогнозом и мета-информацией.
    5. Загружает результат обратно в MinIO.
    6. Возвращает информацию о загруженном файле.
    """
    session_id = str(uuid.uuid4())
    
    try:
        logging.info(f"[train_predict_base64] Начало обработки для session_id={session_id}")
        
        training_params = get_default_training_params()

        if request.target_column:
            training_params.target_column = request.target_column
        if request.training_time_limit is not None:
            training_params.training_time_limit = request.training_time_limit
        if request.problem_type:
            training_params.problem_type = request.problem_type
        if request.evaluation_metric:
            training_params.evaluation_metric = request.evaluation_metric
        
        # Скачиваем файлы из MinIO вместо декодирования base64
        try:
            logging.info(f"Скачивание файла для обучения: {request.train_minio_file_id}")
            train_file_bytes = get_file_from_minio(request.train_minio_file_id)
            logging.info(f"Скачивание файла для прогноза: {request.predict_minio_file_id}")
            predict_file_bytes = get_file_from_minio(request.predict_minio_file_id)
        except HTTPException as e:
            # Перебрасываем ошибку, чтобы FastAPI вернул правильный статус
            raise e
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка получения файлов из MinIO: {str(e)}")
        
        try:
            df_train = pd.read_excel(io.BytesIO(train_file_bytes))
            df_predict = pd.read_excel(io.BytesIO(predict_file_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка чтения Excel файлов: {str(e)}")
        
        logging.info(f"[train_predict_base64] Файлы загружены. Train shape: {df_train.shape}, Predict shape: {df_predict.shape}")
        
        session_path = create_session_directory(session_id)
        
        predict_file_path = os.path.join(session_path, f"test_{session_id}.xlsx")
        df_predict.to_excel(predict_file_path, index=False)
        
        training_sessions[session_id] = {
            "status": "initializing",
            "session_id": session_id,
            "session_path": session_path,
            "predict_file_path": predict_file_path
        }
        
        await run_training_prediction_async(
            session_id=session_id,
            df_train=df_train,
            training_params=training_params,
            original_filename="train_file.xlsx",
            token=None
        )
        
        session_status = training_sessions.get(session_id, {})
        if session_status.get("status") != "completed":
            error_msg = session_status.get("error", "Неизвестная ошибка обучения")
            raise HTTPException(status_code=500, detail=f"Ошибка обучения: {error_msg}")
        
        prediction_file_path = session_status.get("prediction_file")
        if not prediction_file_path or not os.path.exists(prediction_file_path):
            raise HTTPException(status_code=500, detail="Файл с прогнозом не найден")
        
        prediction_df = pd.read_parquet(prediction_file_path)
        
        # Создаём Excel с метаинформацией
        output_buffer = create_excel_with_metadata(prediction_df, session_id)
        
        # --- Загрузка результата в MinIO ---
        # Определяем bucket и папку из исходного файла
        bucket, src_object = request.train_minio_file_id.split('/', 1)
        src_dir = os.path.dirname(src_object)
        
        pred_filename = f"prediction_with_metadata_{session_id}.xlsx"
        pred_object = f"{src_dir}/{pred_filename}" if src_dir else pred_filename
        
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        upload_file_to_minio(
            file_bytes=output_buffer.getvalue(),
            bucket=bucket,
            object_name=pred_object,
            content_type=content_type
        )
        
        # Формируем ответ
        result_file_id = f"{bucket}/{pred_object}"
        
        logging.info(f"[train_predict_base64] Успешно завершено. Результат загружен в {result_file_id}")
        
        return TrainPredictResponse(
            files=[FileResponse(
                fileId=result_file_id,
                fileName=pred_filename,
                mimeType=content_type
            )],
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
    Эта функция остается без изменений, т.к. ее логика не зависит от источника/приемника данных.
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

    # Читаем параметры обучения
    params_dict = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            params_dict = metadata.get("training_parameters", {})
        except Exception as e:
            logging.warning(f"Не удалось прочитать параметры обучения: {e}")

    # Формируем новый Excel-файл с несколькими листами
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Лист 1: Прогноз
        prediction_df.to_excel(writer, sheet_name="Prediction", index=False)
        
        # Лист 2: Leaderboard
        if df_leaderboard is not None:
            df_leaderboard.to_excel(writer, sheet_name="Leaderboard", index=False)
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
        
        # Лист 3: Параметры обучения
        if params_dict is not None:
            pd.DataFrame(list(params_dict.items()), columns=["Parameter", "Value"]).to_excel(writer, sheet_name="TrainingParams", index=False)
        else:
            pd.DataFrame({"info": ["Training parameters not found"]}).to_excel(writer, sheet_name="TrainingParams", index=False)
        
        # Лист 4: Feature Importance
        fi_path = os.path.join(session_path, "autogluon", "feature_importance.csv")
        feature_importance = None
        if os.path.exists(fi_path):
            try:
                feature_importance = pd.read_csv(fi_path).to_dict(orient="records")
            except Exception as e:
                logging.warning(f"Не удалось прочитать feature importance: {e}")
        
        if feature_importance:
            pd.DataFrame(feature_importance).to_excel(writer, sheet_name="FeatureImportance", index=False)
        else:
            pd.DataFrame({"info": ["Feature importance not found"]}).to_excel(writer, sheet_name="FeatureImportance", index=False)
        
        # Лист 5: WeightedEnsemble
        weighted_ensemble_path = os.path.join(session_path, "autogluon", "model_metadata.json")
        if os.path.exists(weighted_ensemble_path):
            try:
                with open(weighted_ensemble_path, "r", encoding="utf-8") as f:
                    model_metadata = json.load(f)
                ensemble_keys = [k for k in ("WeightedEnsemble_L1_weights", "WeightedEnsemble_L2_weights") if k in model_metadata]
                if ensemble_keys:
                    ws = writer.book.add_worksheet("WeightedEnsemble")
                    row = 0
                    for key in ensemble_keys:
                        ws.write(row, 0, key.replace("_weights", ""))
                        row += 1
                        weights = model_metadata[key]
                        if isinstance(weights, dict):
                            ws.write_row(row, 0, ["Model", "Weight"])
                            row += 1
                            for model, weight in weights.items():
                                ws.write(row, 0, f"  {model}")
                                ws.write(row, 1, weight)
                                row += 1
                        else:
                            ws.write(row, 0, "(weights not found or not a dict)")
                            row += 1
                        row += 1 # Пустая строка для разделения
            except Exception as e:
                logging.warning(f"Не удалось добавить WeightedEnsemble: {e}")
    
    output.seek(0)
    return output