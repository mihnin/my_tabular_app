import json
import logging
import os
import threading
from typing import Any

from fastapi import HTTPException
from autogluon.tabular import TabularPredictor

from AutoML.automl import AutoMLStrategy
from sessions.utils import get_session_path, load_session_metadata, save_session_metadata

# Глобальный семафор для ограничения числа одновременных обучений AutoGluon
autogluon_train_semaphore = threading.Semaphore(12)

class AutoGluonStrategy(AutoMLStrategy):
    name = 'autogluon'

    def train(self, df_train: Any, training_params: Any, session_id: str):
        """
        Обучение табличной модели AutoGluon TabularPredictor.
        df_train: pd.DataFrame
        training_params: TrainingParameters (должен содержать label, problem_type, eval_metric, presets, time_limit, models_to_train)
        session_id: str
        """
        session_path = get_session_path(session_id)
        model_path = os.path.join(session_path, 'autogluon')
        os.makedirs(model_path, exist_ok=True)
        label = getattr(training_params, 'target_column', None)
        problem_type = getattr(training_params, 'problem_type', None)
        eval_metric = getattr(training_params, 'evaluation_metric', None)
        presets = getattr(training_params, 'autogluon_preset', 'medium_quality')
        time_limit = getattr(training_params, 'training_time_limit', None)
        models_to_train = getattr(training_params, 'models_to_train', None)

        # Готовим hyperparameters
        if (
            not models_to_train or
            (isinstance(models_to_train, list) and (len(models_to_train) == 0 or '*' in models_to_train or 'all' in models_to_train)) or
            (isinstance(models_to_train, str) and models_to_train.strip() in ('*', 'all'))
        ):
            hyperparams = None  # обучать все модели
        else:
            hyperparams = {m: {} for m in models_to_train}

        try:
            logging.info(f"[AutoGluonStrategy] Старт обучения TabularPredictor для session_id={session_id}")
            predictor = TabularPredictor(
                label=label,
                problem_type=problem_type if problem_type != 'auto' else None,
                eval_metric=eval_metric if eval_metric != 'auto' else None,
                path=model_path
            )
            predictor.fit(
                train_data=df_train,
                time_limit=time_limit,
                presets=presets,
                hyperparameters=hyperparams
            )
            # Сохраняем leaderboard
            leaderboard = predictor.leaderboard(display=False)
            leaderboard_path = os.path.join(model_path, 'leaderboard.csv')
            # Удаляем строки, где все значения метрик (например, score_val) — NaN
            metric_cols = [col for col in leaderboard.columns if col.startswith('score')]
            if metric_cols:
                leaderboard = leaderboard.dropna(subset=metric_cols, how='all')
            leaderboard.to_csv(leaderboard_path, index=False)
            # Сохраняем fit_summary
            fit_summary = predictor.fit_summary()
            # Сохраняем feature importance
            try:
                fi = predictor.feature_importance(df_train)
                if 'feature' not in fi.columns:
                    fi.insert(0, 'feature', fi.index)
                fi_path = os.path.join(model_path, 'feature_importance.csv')
                fi.to_csv(fi_path, index=False)
            except Exception as e:
                logging.warning(f"[AutoGluonStrategy] Не удалось сохранить feature importance: {e}")
            # Преобразуем все DataFrame в fit_summary в dict
            def convert_df(obj):
                if isinstance(obj, dict):
                    return {k: convert_df(v) for k, v in obj.items()}
                elif hasattr(obj, 'to_dict') and callable(obj.to_dict):
                    try:
                        return obj.to_dict(orient='records')
                    except Exception:
                        return str(obj)
                elif isinstance(obj, list):
                    return [convert_df(v) for v in obj]
                else:
                    return obj
            fit_summary_serializable = convert_df(fit_summary)
            with open(os.path.join(model_path, 'fit_summary.json'), 'w', encoding='utf-8') as f:
                json.dump(fit_summary_serializable, f, ensure_ascii=False, indent=2)
            # Сохраняем статус
            meta = load_session_metadata(session_id)
            if meta is not None:
                meta['status'] = 'completed'
                meta['model_path'] = model_path
                save_session_metadata(session_id, meta)
            logging.info(f"[AutoGluonStrategy] Обучение завершено для session_id={session_id}")
        except Exception as e:
            logging.error(f"[AutoGluonStrategy] Ошибка обучения: {e}", exc_info=True)
            meta = load_session_metadata(session_id)
            if meta is not None:
                meta['status'] = 'failed'
                meta['error'] = str(e)
                save_session_metadata(session_id, meta)
            raise

    def predict(self, df: Any, session_id: str, training_params: Any):
        """
        Предсказание для табличных данных с помощью TabularPredictor.
        df: pd.DataFrame
        session_id: str
        training_params: TrainingParameters (используется только для метаданных)
        """
        session_path = get_session_path(session_id)
        model_path = os.path.join(session_path, 'autogluon')
        if not os.path.exists(model_path):
            logging.error(f"Папка с моделью не найдена: {model_path}")
            raise HTTPException(status_code=404, detail="Папка с моделью не найдена")
        try:
            predictor = TabularPredictor.load(model_path)
            logging.info(f"Модель TabularPredictor успешно загружена из {model_path}")
        except Exception as e:
            logging.error(f"Ошибка загрузки модели: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки модели: {e}")
        try:
            # --- Drop target column if present ---
            target_col = None
            if hasattr(training_params, 'target_column'):
                target_col = getattr(training_params, 'target_column', None)
            elif isinstance(training_params, dict):
                target_col = training_params.get('target_column')
            if target_col and target_col in df.columns:
                df = df.drop(columns=[target_col])
            preds = predictor.predict(df)
            # Если Series, преобразуем в DataFrame
            if hasattr(preds, 'to_frame'):
                preds = preds.to_frame('prediction')
            # Переименовываем колонку 'prediction' в имя целевой колонки
            if target_col and 'prediction' in preds.columns:
                preds = preds.rename(columns={'prediction': target_col})
            # Конкатенируем с исходными данными
            out_df = df.reset_index(drop=True).copy()
            preds = preds.reset_index(drop=True)
            result = out_df.join(preds)
            return result
        except Exception as e:
            logging.error(f"Ошибка при прогнозировании: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка при прогнозировании: {e}")

autogluon_strategy = AutoGluonStrategy()