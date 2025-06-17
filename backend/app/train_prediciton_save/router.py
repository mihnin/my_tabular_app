from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form, BackgroundTasks, Request
import pandas as pd
import numpy as np
import logging
import gc
import os
import json
import uuid
import asyncio
from functools import partial
from typing import Dict, Optional
from datetime import datetime
from io import BytesIO

from db.db_manager import upload_df_to_db
from db.jwt_logic import get_current_user_db_creds
from db.db_manager import auto_convert_dates
from prediction.router import save_prediction
from training.model import TrainingParameters
from training.router import train_model, get_training_status, prepare_training_data_and_status, optional_oauth2_scheme
from sessions.utils import (
    create_session_directory,
    save_session_metadata,
    cleanup_old_sessions,
    get_model_path,
    training_sessions
)
from prediction.router import predict_tabular
# Global training status tracking

# Run cleanup of old sessions at startup
cleanup_old_sessions()

router = APIRouter()

async def run_training_prediction_async(
    session_id: str,
    df_train: pd.DataFrame,
    training_params: TrainingParameters,
    original_filename: str,
    token: str
):
    """Асинхронный запуск процесса обучения и (опционально) прогноза с сохранением в БД для табличных данных."""
    try:
        logging.info(f"[run_training_prediction_async] Запуск обучения для session_id={session_id}, файл: {original_filename}")
        session_path = create_session_directory(session_id)
        status = training_sessions[session_id]
        status.update({
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "progress": 0,
            "session_path": session_path,
            "original_filename": original_filename,
            "training_parameters": training_params.model_dump()
        })
        save_session_metadata(session_id, status)

        # 1. Обучение
        text_to_progress = {
            'preparation': 10,
            'missings': 20,
            'dataframe': 30,
            'training': 40,
            'metadata': 50
        }
        train_func = partial(
            train_model,
            df_train=df_train,
            training_params=training_params,
            model_path=get_model_path(session_id),
            session_id=session_id,
            text_to_progress=text_to_progress
        )
        logging.info(f"[run_training_prediction_async] Передача задачи обучения в пул потоков...")
        await asyncio.to_thread(train_func)

        status.update({
            "status": "Обучение окончено. Начинаем прогноз",
            "end_time": datetime.now().isoformat(),
            "progress": 60,
            "model_path": get_model_path(session_id),
            "training_parameters": training_params.model_dump()
        })
        save_session_metadata(session_id, status)
        training_sessions[session_id] = status
        logging.info(f"[run_training_prediction_async] Обучение завершено успешно для session_id={session_id}")

        # 2. Прогноз
        prediction_df = await asyncio.to_thread(predict_tabular, session_id)
        prediction_parquet_path = os.path.join(session_path, f"prediction_{session_id}.parquet")
        prediction_df.to_parquet(prediction_parquet_path, index=False)
        # Restore prediction_head logic: save first 10 rows for preview
        prediction_head = prediction_df.head(10).to_dict(orient="records")
        # --- АТОМАРНОЕ обновление статуса: только после формирования prediction_head ---
        status["prediction_file"] = prediction_parquet_path
        status["prediction_head"] = prediction_head
        status["progress"] = 100
        status["status"] = "completed"
        save_session_metadata(session_id, status)
        training_sessions[session_id] = status
        logging.info(f"[run_training_prediction_async] Прогноз завершен и сохранен для session_id={session_id}")

        # 3. (опционально) Сохранение в БД, если требуется
        if getattr(training_params, 'upload_table_name', None):
            logging.info(f"[run_training_prediction_async] Начинается сохранение прогноза в БД для session_id={session_id}")
            preds = prediction_df
            table_name = getattr(training_params, 'upload_table_name')
            schema = getattr(training_params, 'upload_table_schema', None)
            db_creds = None
            if token is not None:
                db_creds = await get_current_user_db_creds(token)
            else:
                raise ValueError("Не передан токен для получения учетных данных БД")
            username = db_creds["username"]
            password = db_creds["password"]
            preds = auto_convert_dates(preds)
            if schema:
                await upload_df_to_db(preds, schema, table_name, username, password)
            else:
                await upload_df_to_db(preds, table_name, username, password)
            logging.info(f"[run_training_prediction_async] Прогноз успешно загружен в таблицу '{table_name}' базы данных (схема: {schema}).")

    except Exception as e:
        error_msg = str(e)
        logging.error(f"[run_training_prediction_async] Ошибка обучения/прогноза в сессии {session_id}: {error_msg}", exc_info=True)
        status = training_sessions[session_id]
        status.update({
            "status": "failed",
            "error": error_msg,
            "end_time": datetime.now().isoformat()
        })
        save_session_metadata(session_id, status)
        training_sessions[session_id] = status


def save_df_to_parquet(df, path):
    df.to_parquet(path)




@router.post("/train_prediction_save/")
async def train_model_endpoint(
    request: Request,
    params: str = Form(...),
    train_file: UploadFile = File(None),
    test_file: UploadFile = File(None),
    background_tasks: BackgroundTasks = None,
    token: Optional[str] = Depends(optional_oauth2_scheme),
):
    """Запуск асинхронного процесса обучения и возврат session_id для отслеживания статуса.
    Если в параметрах есть download_table_name, то датасет берется из БД, иначе из файла.
    Аутентификация требуется только для загрузки из БД.
    """
    session_id = str(uuid.uuid4())
    try:
        logging.info(f"[train_model_endpoint] Получен запрос на обучение. Файл: {getattr(train_file, 'filename', None)}, Session ID: {session_id}")
        if train_file:
            logging.info(f"[train_model_endpoint] train_file.filename: {train_file.filename}")
        params_dict = json.loads(params)
        training_params = TrainingParameters(**params_dict)
        logging.info(f"[train_model_endpoint] Параметры обучения для session_id={session_id}: {params_dict}")

        # Используем общую функцию подготовки данных и статуса
        df_train, training_params, session_path, status = prepare_training_data_and_status(
            params,
            train_file,
            test_file,
            session_id
        )
        original_filename = train_file.filename if train_file else None
        logging.info(f"[train_model_endpoint] Статус сессии и метаданные сохранены для session_id={session_id}")

        # Start async training
        background_tasks.add_task(
            run_training_prediction_async,
            session_id,
            df_train,
            training_params,
            original_filename,
            token
        )
        logging.info(f"[train_model_endpoint] Задача обучения передана в background_tasks для session_id={session_id}")
        return {
            "status": "accepted",
            "message": "Обучение запущено",
            "session_id": session_id
        }

    except json.JSONDecodeError as e:
        logging.error(f"Ошибка разбора JSON параметров для session_id={session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка разбора JSON параметров: {str(e)}"
        )
    except ValueError as e:
        logging.error(f"Ошибка валидации параметров для session_id={session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Ошибка валидации параметров: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при запуске обучения для session_id={session_id}: {e}", exc_info=True)
        if session_id in training_sessions:
            failed_status = {
                "status": "failed",
                "error": f"Ошибка на этапе инициализации: {str(e)}",
                "end_time": datetime.now().isoformat()
            }
            training_sessions[session_id].update(failed_status)
            save_session_metadata(session_id, training_sessions[session_id])
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера при запуске обучения: {str(e)}"
        )
    finally:
        if train_file:
            await train_file.close()
        if test_file:
            await test_file.close()