import json
from fastapi import APIRouter, HTTPException, Response
import os
import pandas as pd
from io import BytesIO
import logging
from AutoML.manager import automl_manager
import asyncio
from src.features.feature_engineering import fill_missing_values
from sessions.utils import (
    get_session_path,
    load_session_metadata,
)

router = APIRouter()

def predict_tabular(session_id: str):
    logging.info(f"[predict_tabular] Начало прогноза для session_id={session_id}")
    session_path = get_session_path(session_id)
    if not os.path.exists(session_path):
        logging.error(f"Папка сессии не найдена: {session_path}")
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    metadata = load_session_metadata(session_id)
    if not metadata:
        logging.error(f"Файл metadata.json не найден для session_id={session_id}")
        raise HTTPException(status_code=404, detail="metadata.json не найден")
    params = metadata.get("training_parameters")
    if not params:
        logging.error(f"Параметры обучения не найдены в metadata.json для session_id={session_id}")
        raise HTTPException(status_code=400, detail="Параметры обучения не найдены в metadata.json")

    # Поиск test файла (csv/xlsx/xls) для прогноза
    test_file = None
    for fname in os.listdir(session_path):
        if fname.startswith('test_') and (fname.endswith('.csv') or fname.endswith('.xlsx') or fname.endswith('.xls')):
            test_file = os.path.join(session_path, fname)
            break
    if not test_file:
        logging.error(f"Файл test не найден для session_id={session_id}")
        raise HTTPException(status_code=404, detail="Файл test не найден для прогноза")
    file_to_predict = test_file
    logging.info(f"Файл test найден и будет использован для прогноза: {test_file}")
    try:
        if file_to_predict.endswith('.csv'):
            df = pd.read_csv(file_to_predict)
        else:
            df = pd.read_excel(file_to_predict)
        logging.info(f"Файл для прогноза успешно загружен: {file_to_predict}")
    except Exception as e:
        logging.error(f"Ошибка чтения файла для прогноза: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка чтения файла для прогноза: {e}")

    # Препроцессинг (если нужно, например, fill_missing_values)
    fill_method = params.get("fill_missing_method", None)
    if fill_method:
        df = fill_missing_values(df, fill_method)
        logging.info(f"Пропущенные значения обработаны методом: {fill_method}")

    # Предсказание
    if len(df) != 0:
        best_strategy = automl_manager.get_best_strategy(session_id)
        preds = best_strategy.predict(df, session_id, params)
    else:
        preds = pd.DataFrame()
    return preds

def save_prediction(output, session_id):
    session_path = get_session_path(session_id)
    prediction_file_path = os.path.join(session_path, f"prediction_{session_id}.xlsx")
    with open(prediction_file_path, "wb") as f:
        f.write(output.getvalue())
    logging.info(f"[predict_tabular] Прогноз сохранён в файл: {prediction_file_path}")

@router.get("/predict/{session_id}")
async def predict_tabular_endpoint(session_id: str):
    """Сделать прогноз по id сессии: сохранить полный прогноз в Parquet, вернуть только 10 строк в JSON."""
    preds = await asyncio.to_thread(predict_tabular, session_id)
    session_path = get_session_path(session_id)
    prediction_parquet_path = os.path.join(session_path, f"prediction_{session_id}.parquet")
    preds.to_parquet(prediction_parquet_path, index=False)
    # Возвращаем только первые 10 строк как JSON
    head = preds.head(10).to_dict(orient="records")
    return {"prediction_head": head}

@router.get("/download_prediction/{session_id}")
def download_prediction_file(session_id: str):
    """Скачать ранее сохранённый файл прогноза по id сессии с добавлением leaderboard и параметров обучения."""
    logging.info(f"[download_prediction_file] Запрос на скачивание xlsx для session_id={session_id}")
    session_path = get_session_path(session_id)
    prediction_parquet_path = os.path.join(session_path, f"prediction_{session_id}.parquet")
    leaderboard_path = os.path.join(session_path, "leaderboard.csv")
    metadata_path = os.path.join(session_path, "metadata.json")
    feature_importance_path = os.path.join(session_path, "feature_importance.csv")

    # Проверяем наличие файла прогноза
    if not os.path.exists(prediction_parquet_path):
        logging.error(f"Файл прогноза не найден: {prediction_parquet_path}")
        raise HTTPException(status_code=404, detail="Файл прогноза не найден")

    # Читаем прогноз
    try:
        df_pred = pd.read_parquet(prediction_parquet_path)
    except Exception as e:
        logging.error(f"Ошибка чтения файла прогноза: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка чтения файла прогноза: {e}")

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
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Первый лист — прогноз
        df_pred.to_excel(writer, sheet_name="Prediction", index=False)
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
                logging.warning(f"[download_prediction_file] Не удалось выделить лучшую строку в leaderboard: {e}")
        else:
            pd.DataFrame({"info": ["Leaderboard not found"]}).to_excel(writer, sheet_name="Leaderboard", index=False)
        # Третий лист — параметры обучения
        if params_dict is not None:
            pd.DataFrame(list(params_dict.items()), columns=["Parameter", "Value"]).to_excel(writer, sheet_name="TrainingParams", index=False)
        else:
            pd.DataFrame({"info": ["Training parameters not found"]}).to_excel(writer, sheet_name="TrainingParams", index=False)
        # Четвёртый лист — feature_importance (берём как в get_training_status)
        fi_path = os.path.join(session_path, "autogluon", "feature_importance.csv")
        feature_importance = None
        if os.path.exists(fi_path):
            try:
                feature_importance = pd.read_csv(fi_path).to_dict(orient="records")
                logging.info(f"[download_prediction_file] Feature importance добавлен для session_id={session_id}")
            except Exception as e:
                logging.warning(f"[download_prediction_file] Не удалось прочитать feature importance: {e}")
        if feature_importance and isinstance(feature_importance, list) and len(feature_importance) > 0:
            try:
                df_fi = pd.DataFrame(feature_importance)
                df_fi.to_excel(writer, sheet_name="FeatureImportance", index=False)
            except Exception as e:
                pd.DataFrame({"info": [f"Feature importance error: {e}"]}).to_excel(writer, sheet_name="FeatureImportance", index=False)
        else:
            pd.DataFrame({"info": ["Feature importance not found"]}).to_excel(writer, sheet_name="FeatureImportance", index=False)
        # Пятый лист — WeightedEnsemble (все уровни, без жёсткой привязки к L1/L2)
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
                logging.warning(f"[download_prediction_file] Не удалось добавить WeightedEnsemble: {e}")
    output.seek(0)

    logging.info(f"[download_prediction_file] Мульти-листовой Excel-файл отправлен: prediction_{session_id}.xlsx")
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=prediction_{session_id}.xlsx"
        }
    )

@router.get("/download_prediction_csv/{session_id}")
def download_prediction_csv_file(session_id: str):
    """Скачать ранее сохранённый файл прогноза в формате CSV по id сессии."""
    logging.info(f"[download_prediction_csv_file] Запрос на скачивание csv для session_id={session_id}")
    session_path = get_session_path(session_id)
    prediction_parquet_path = os.path.join(session_path, f"prediction_{session_id}.parquet")
    if not os.path.exists(prediction_parquet_path):
        logging.error(f"Файл прогноза (parquet) не найден: {prediction_parquet_path}")
        raise HTTPException(status_code=404, detail="Файл прогноза не найден")
    try:
        df = pd.read_parquet(prediction_parquet_path)
        output = BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
    except Exception as e:
        logging.error(f"Ошибка при формировании CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при формировании CSV: {e}")
    logging.info(f"[download_prediction_csv_file] CSV-файл отправлен: prediction_{session_id}.csv")
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=prediction_{session_id}.csv"
        }
    )

@router.get("/predict_head/{session_id}")
def predict_head_endpoint(session_id: str):
    """Возвращает первые 10 строк прогноза для превью (JSON)."""
    session_path = get_session_path(session_id)
    prediction_parquet_path = os.path.join(session_path, f"prediction_{session_id}.parquet")
    if not os.path.exists(prediction_parquet_path):
        raise HTTPException(status_code=404, detail="Файл прогноза не найден")
    try:
        df = pd.read_parquet(prediction_parquet_path)
        head = df.head(10).to_dict(orient="records")
        return {"prediction_head": head}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения файла прогноза: {e}")
