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
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from .model import TrainingParameters
from src.features.feature_engineering import fill_missing_values
from sessions.utils import (
    create_session_directory,
    get_session_path,
    save_session_metadata,
    load_session_metadata,
    cleanup_old_sessions,
    save_training_file,
    get_model_path,
    training_sessions
)
from AutoML.manager import automl_manager



# Run cleanup of old sessions at startup
cleanup_old_sessions()

router = APIRouter()

def get_training_status(session_id: str) -> Optional[Dict]:
    """Get the current status of a training session."""
    try:
        metadata = load_session_metadata(session_id)
        if metadata:
            training_sessions[session_id] = metadata  # обновляем кэш, если нужно
        return metadata
    except:
        return None

async def run_training_async(
    session_id: str,
    df_train: pd.DataFrame,
    training_params: TrainingParameters,
    original_filename: str,
):
    """Асинхронный запуск процесса обучения."""
    try:
        logging.info(f"[run_training_async] Запуск обучения для session_id={session_id}, файл: {original_filename}")
        # Create session directory and save initial status
        session_path = get_session_path(session_id)
        status = {
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "progress": 0,
            "session_path": session_path,
            "original_filename": original_filename,
            "training_parameters": training_params.model_dump() 
        }
        training_sessions[session_id] = status
        save_session_metadata(session_id, status)

        status.update({"progress": 10})
        save_session_metadata(session_id, status)
        
        # 2. Setup model directory
        model_path = get_model_path(session_id)
        os.makedirs(model_path, exist_ok=True)
        logging.info(f"[run_training_async] Каталог модели создан: {model_path}")

        # Run the actual training process in a thread pool

        text_to_progress = {
            'preparation': 20,
            'holidays': 30,
            'missings': 40,
            'dataframe': 50,
            'training': 60,
            'metadata': 90
        }

        train_func = partial(
            train_model,
            df_train=df_train,
            training_params=training_params,
            model_path=model_path,
            session_id=session_id,
            text_to_progress=text_to_progress
        )
        logging.info(f"[run_training_async] Передача задачи обучения в пул потоков...")
        await asyncio.to_thread(train_func)

        # Update final status
        status.update({
            "status": "completed",
            "end_time": datetime.now().isoformat(),
            "progress": 100,
            "model_path": model_path,
            "training_parameters": training_params.model_dump()  # сохраняем параметры обучения в финальном статусе
        })
        save_session_metadata(session_id, status)
        training_sessions[session_id] = status
        logging.info(f"[run_training_async] Обучение завершено успешно для session_id={session_id}")

    except Exception as e:
        error_msg = str(e)
        logging.error(f"[run_training_async] Ошибка обучения в сессии {session_id}: {error_msg}", exc_info=True)
        status = training_sessions[session_id]
        status.update({
            "status": "failed",
            "error": error_msg,
            "end_time": datetime.now().isoformat()
        })
        save_session_metadata(session_id, status)
        training_sessions[session_id] = status

def train_model(
    df_train: pd.DataFrame,
    training_params: TrainingParameters,
    model_path: str,
    session_id: str,
    text_to_progress: dict | None
) -> None:
    """Основная функция обучения (запускается в отдельном потоке)."""
    try:
        status = training_sessions[session_id]
        logging.info(f"[train_model] Начало подготовки данных для session_id={session_id}")
        # Data Preparation (только для табличных данных)
        df2 = df_train.copy()
        # Обработка пропусков (если нужно)
        df2 = fill_missing_values(
            df2,
            getattr(training_params, 'fill_missing_method', None),
        )

        logging.info(f"[train_model] Пропущенные значения обработаны методом: {getattr(training_params, 'fill_missing_method', None)}")

        status.update({"progress": text_to_progress['missings']})
        
        save_session_metadata(session_id, status)

        if len(df2) != 0:
            for strategy in automl_manager.get_strategies():
                strategy.train(df2, training_params, session_id)

        session_path = get_session_path(session_id)
        combined_leaderboard = automl_manager.combine_leaderboards(session_id, [s.name for s in automl_manager.get_strategies()])
        combined_leaderboard.to_csv(os.path.join(session_path, 'leaderboard.csv'), index=False)
        gc.collect()
        logging.info(f"[train_model] Очистка памяти завершена.")
    except Exception as e:
        logging.error(f"[train_model] Ошибка в процессе обучения: {e}", exc_info=True)
        raise Exception(f"Error in training process: {str(e)}")


@router.get("/training_status/{session_id}")
async def get_session_status(session_id: str):
    """Получить статус сессии обучения. Если завершено — добавить лидерборд."""
    logging.info(f"[get_training_status] Запрос статуса для session_id={session_id}")
    status = get_training_status(session_id)
    if status is None:
        logging.error(f"Сессия не найдена: {session_id}")
        raise HTTPException(status_code=404, detail="Training session not found")
    session_path = get_session_path(session_id)
    if status.get("status") == "completed":
        leaderboard_path = os.path.join(session_path, "leaderboard.csv")
        leaderboard = None
        if os.path.exists(leaderboard_path):
            leaderboard = pd.read_csv(leaderboard_path).to_dict(orient="records")
            logging.info(f"[get_training_status] Лидерборд добавлен к статусу для session_id={session_id}")
        status["leaderboard"] = leaderboard
        # Добавляем feature importance
        fi_path = os.path.join(session_path, "autogluon", "feature_importance.csv")
        feature_importance = None
        if os.path.exists(fi_path):
            try:
                feature_importance = pd.read_csv(fi_path).to_dict(orient="records")
                logging.info(f"[get_training_status] Feature importance добавлен к статусу для session_id={session_id}")
            except Exception as e:
                logging.warning(f"[get_training_status] Не удалось прочитать feature importance: {e}")
        status["feature_importance"] = feature_importance
    return status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def optional_oauth2_scheme(request: Request) -> Optional[str]:
    """
    Позволяет получать токен, если он есть, иначе возвращает None (для публичных эндпоинтов).
    """
    auth: str = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1]
    return None

@router.post("/train_tabular")
async def train_tabular_endpoint(
    request: Request,
    params: str = Form(...),
    train_file: UploadFile = File(None),
    test_file: UploadFile = File(None),
    background_tasks: BackgroundTasks = None,
):
    """
    Эндпоинт для обучения табличных данных (AutoGluon Tabular).
    Принимает параметры обучения одним JSON-стрингом (params), два файла (train_file, test_file), сохраняет их в сессию и запускает обучение.
    Возвращает session_id для отслеживания статуса.
    """
    try:
        # Вся подготовка вынесена в функцию ниже
        df_train, training_params, session_path, status = prepare_training_data_and_status(
            params, train_file, test_file
        )
        session_id = status['session_id']
        # Запускаем обучение через run_training_async в фоне
        if background_tasks is not None:
            background_tasks.add_task(run_training_async, session_id, df_train, training_params, train_file.filename)
        else:
            import threading
            threading.Thread(target=lambda: asyncio.run(run_training_async(session_id, df_train, training_params, train_file.filename)), daemon=True).start()
        return {"session_id": session_id}
    except Exception as e:
        logging.error(f"[train_tabular_endpoint] Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def prepare_training_data_and_status(
    params: str,
    train_file: UploadFile = None,
    test_file: UploadFile = None,
    session_id: str = None
):
    """
    Универсальная функция подготовки данных и статуса для обучения (используется в train_prediction_save).
    Возвращает: df_train, training_params, session_path, status
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    session_path = create_session_directory(session_id)
    params_dict = json.loads(params)
    training_params = TrainingParameters(**params_dict)
    # Сохраняем train файл
    if train_file is not None:
        train_path = os.path.join(session_path, f"train_{train_file.filename}")
        train_bytes = train_file.file.read() if hasattr(train_file, 'file') else train_file.read()
        with open(train_path, "wb") as f:
            f.write(train_bytes)
    else:
        raise HTTPException(status_code=400, detail="train_file is required")
    # Сохраняем test файл (если есть)
    if test_file is not None:
        test_path = os.path.join(session_path, f"test_{test_file.filename}")
        test_bytes = test_file.file.read() if hasattr(test_file, 'file') else test_file.read()
        with open(test_path, "wb") as f:
            f.write(test_bytes)
    # Читаем train в DataFrame
    def read_df(path):
        if path.endswith('.csv'):
            return pd.read_csv(path)
        elif path.endswith('.xlsx') or path.endswith('.xls'):
            return pd.read_excel(path)
        else:
            raise ValueError("Файл должен быть .csv или .xlsx/.xls")
    df_train = read_df(train_path)
    # Проверяем наличие целевой переменной
    if not training_params.target_column:
        raise HTTPException(status_code=400, detail="target_column must be specified in params")
    if training_params.target_column not in df_train.columns:
        raise HTTPException(status_code=400, detail=f"В train-файле должна быть колонка '{training_params.target_column}'")
    # Сохраняем начальный статус
    status = {
        'status': 'running',
        'session_id': session_id,
        'train_file': train_file.filename if train_file else None,
        'test_file': test_file.filename if test_file else None,
        'session_path': session_path,
        'training_parameters': params_dict
    }
    save_session_metadata(session_id, status)
    training_sessions[session_id] = status
    return df_train, training_params, session_path, status