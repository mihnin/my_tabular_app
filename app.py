import streamlit as st
import plotly.express as px
import pandas as pd
import logging
import shutil
import yaml
import os
import json

from autogluon.tabular import TabularPredictor
from openpyxl.styles import PatternFill

# Импорт функций обработки данных, инженерии признаков и прогнозирования
from src.data.data_processing import (
    load_data,
    show_dataset_stats
)
from src.features.feature_engineering import (
    fill_missing_values
)
from src.models.prediction import (
    predict_tabular
)
from src.utils.utils import (
    setup_logger,
    read_logs
)
from src.help_page import show_help_page

CONFIG_PATH = "config/config.yaml"
MODEL_DIR = "AutogluonModels/TabularModel"
MODEL_INFO_FILE = "model_info.json"


def load_config(path: str):
    """Загружает YAML конфигурацию (METRICS_DICT, AG_MODELS)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Конфигурационный файл {path} не найден.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    metrics_dict = data.get("metrics_dict", {})
    ag_models = data.get("ag_models", {})
    presets_list = data.get("presets_list", []) # Добавлен список пресетов из конфигурации
    return metrics_dict, ag_models, presets_list


METRICS_DICT, AG_MODELS, PRESETS_LIST = load_config(CONFIG_PATH)


def save_model_metadata(tgt_col, problem_type, eval_metric, fill_method_val, group_cols_fill_val,
                       presets, chosen_models):
    """Сохраняет все настройки (колонки, тип задачи, метрика и т.д.) в JSON."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    info_dict = {
        "tgt_col": tgt_col,
        "problem_type": problem_type,
        "eval_metric": eval_metric,
        "fill_method_val": fill_method_val,
        "group_cols_fill_val": group_cols_fill_val,
        "presets": presets,
        "chosen_models": chosen_models,
    }
    path_json = os.path.join(MODEL_DIR, MODEL_INFO_FILE)
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(info_dict, f, ensure_ascii=False, indent=2)


def load_model_metadata():
    """Загружает сохраненные настройки из model_info.json, если доступно."""
    path_json = os.path.join(MODEL_DIR, MODEL_INFO_FILE)
    if not os.path.exists(path_json):
        return None
    try:
        with open(path_json, "r", encoding="utf-8") as f:
            info = json.load(f)
        return info
    except:
        return None


def try_load_existing_model():
    """Загружает предварительно обученный TabularPredictor, если доступен в MODEL_DIR."""
    if not os.path.exists(MODEL_DIR):
        return
    try:
        loaded_predictor = TabularPredictor.load(MODEL_DIR)
        st.session_state["predictor"] = loaded_predictor
        st.info(f"Загружена ранее обученная модель из {MODEL_DIR}")

        meta = load_model_metadata()
        if meta:
            st.session_state["tgt_col_key"] = meta.get("tgt_col", "<нет>")
            st.session_state["problem_type_key"] = meta.get("problem_type", "auto")
            st.session_state["eval_metric_key"] = meta.get("eval_metric", "auto")
            st.session_state["fill_method_key"] = meta.get("fill_method_val", "None")
            st.session_state["group_cols_for_fill_key"] = meta.get("group_cols_fill_val", [])
            st.session_state["presets_key"] = meta.get("presets", "medium_quality")
            st.session_state["models_key"] = meta.get("chosen_models", ["* (all)"])

            st.info("Настройки (колонки, тип задачи, метрика и т.д.) восстановлены из model_info.json")
    except Exception as e:
        st.warning(f"Не удалось автоматически загрузить модель из {MODEL_DIR}. Ошибка: {e}")


def main():
    setup_logger()
    logging.info("=== Запуск Streamlit Tabular App (main) ===")

    if "predictor" not in st.session_state or st.session_state["predictor"] is None:
        try_load_existing_model()

    pages = ["Главная", "Help"]
    choice = st.sidebar.selectbox("Навигация", pages, key="page_choice")

    if choice == "Help":
        show_help_page()
        return

    st.title("AutoGluon Tabular App")

    # Инициализация ключей session_state
    if "df" not in st.session_state:
        st.session_state["df"] = None
    if "df_predict" not in st.session_state:
        st.session_state["df_predict"] = None
    if "predictor" not in st.session_state:
        st.session_state["predictor"] = None
    if "leaderboard" not in st.session_state:
        st.session_state["leaderboard"] = None
    if "predictions" not in st.session_state:
        st.session_state["predictions"] = None
    if "fit_summary" not in st.session_state:
        st.session_state["fit_summary"] = None
    if "feature_importance" not in st.session_state: # для важности признаков
        st.session_state["feature_importance"] = None

    if "best_model_name" not in st.session_state:
        st.session_state["best_model_name"] = None
    if "best_model_score" not in st.session_state:
        st.session_state["best_model_score"] = None

    # ========== 1) Загрузка данных ==========
    st.sidebar.header("1. Загрузка данных")
    train_file = st.sidebar.file_uploader("Тренировочные данные (обязательно)", type=["csv", "xls", "xlsx"], key="train_file_uploader")
    predict_file = st.sidebar.file_uploader("Данные для прогнозирования (обязательно)", type=["csv", "xls", "xlsx"], key="predict_file_uploader") # Теперь обязательно

    if st.sidebar.button("Загрузить данные", key="load_data_btn"):
        if not train_file:
            st.error("Тренировочный файл обязателен!")
        elif not predict_file: # Проверка на наличие predict_file
            st.error("Файл для прогнозирования обязателен!")
        else:
            try:
                df_train = load_data(train_file)
                st.session_state["df"] = df_train
                st.success("Тренировочный файл успешно загружен!")
                st.dataframe(df_train.head())

                st.subheader("Статистика тренировочных данных")
                show_dataset_stats(df_train)

                df_predict = load_data(predict_file) # Данные для прогнозирования теперь обязательны
                st.session_state["df_predict"] = df_predict
                st.success("Файл для прогнозирования успешно загружен!")
                st.dataframe(df_predict.head())

                st.subheader("Статистика данных для прогнозирования")
                show_dataset_stats(df_predict)

            except Exception as e:
                st.error(f"Ошибка загрузки данных: {e}")

    # ========== 2) Настройка колонок ==========
    st.sidebar.header("2. Настройка колонок")
    df_current = st.session_state["df"]
    if df_current is not None:
        all_cols = list(df_current.columns)
    else:
        all_cols = []

    tgt_stored = st.session_state.get("tgt_col_key", "<нет>")
    if tgt_stored not in ["<нет>"] + all_cols:
        st.session_state["tgt_col_key"] = "<нет>"

    tgt_col = st.sidebar.selectbox("Целевая колонка", ["<нет>"] + all_cols, key="tgt_col_key")

    problem_type_options = ["auto", "binary", "multiclass", "regression"]
    problem_type = st.sidebar.selectbox("Тип задачи", problem_type_options, index=0, key="problem_type_key")

    eval_metric_options = ["auto"] + list(METRICS_DICT.keys())
    eval_metric = st.sidebar.selectbox("Метрика оценки", eval_metric_options, index=0, key="eval_metric_key")


    # ========== 3) Обработка пропущенных значений ==========
    st.sidebar.header("3. Обработка пропущенных значений")
    fill_options = ["None", "Constant=0", "Mean", "Median", "Mode"] # Удалены Group Mean, Forward Fill как менее релевантные для табличных данных
    fill_method = st.sidebar.selectbox("Метод заполнения пропущенных значений", fill_options, key="fill_method_key")
    group_cols_for_fill = [] # Группировка менее релевантна для общих табличных данных, удалена из интерфейса

    # ========== 4) Настройки модели и обучения ==========
    st.sidebar.header("4. Настройки модели и обучения")

    model_keys = list(AG_MODELS.keys())
    model_choices = ["* (all)"] + model_keys
    chosen_models = st.sidebar.multiselect(
        "Модели AutoGluon",
        model_choices,
        default=st.session_state.get("models_key", ["* (all)"]),
        key="models_key"
    )

    presets = st.sidebar.selectbox("Пресеты", PRESETS_LIST,
                                   index=PRESETS_LIST.index(st.session_state.get("presets_key", "medium_quality")),
                                   key="presets_key")

    time_limit = st.sidebar.number_input("Лимит времени обучения (секунды)", 10, 36000, 60, key="time_limit_key")


    # ========== 5) Обучение модели ==========
    st.sidebar.header("5. Обучение модели")
    if st.sidebar.button("Обучить модель", key="fit_model_btn"):
        df_train = st.session_state.get("df")
        if df_train is None:
            st.warning("Пожалуйста, загрузите тренировочные данные сначала!")
        elif tgt_col == "<нет>":
            st.error("Пожалуйста, выберите целевую колонку!")
        else:
            try:
                shutil.rmtree("AutogluonModels", ignore_errors=True)

                fill_method_val = st.session_state.get("fill_method_key", "None")
                group_cols_val = st.session_state.get("group_cols_for_fill_key", []) # Не используется в интерфейсе больше
                chosen_metric_val = st.session_state.get("eval_metric_key")
                chosen_models_val = st.session_state.get("models_key")
                presets_val = st.session_state.get("presets_key", "medium_quality")
                t_limit = st.session_state.get("time_limit_key", 60)
                problem_type_val = st.session_state.get("problem_type_key")


                df2 = df_train.copy()
                df2 = fill_missing_values(df2, fill_method_val) # Групповые колонки удалены

                hyperparameters = None
                all_models_opt = "* (all)"
                if (len(chosen_models_val) == 1 and chosen_models_val[0] == all_models_opt) or len(chosen_models_val) == 0:
                    hyperparameters = None
                else:
                    no_star = [m for m in chosen_models_val if m != all_models_opt]
                    hyperparameters = {m: {} for m in no_star}

                eval_key = chosen_metric_val if chosen_metric_val != "auto" else None

                predictor = TabularPredictor(
                    label=tgt_col,
                    problem_type=problem_type_val if problem_type_val != "auto" else None,
                    eval_metric=eval_key,
                    path=MODEL_DIR
                )

                st.info("Обучение модели...")
                predictor.fit(
                    train_data=df2,
                    time_limit=t_limit,
                    presets=presets_val,
                    hyperparameters=hyperparameters
                )

                st.session_state["predictor"] = predictor
                st.success("Модель успешно обучена!")

                lb = predictor.leaderboard(df2)
                st.session_state["leaderboard"] = lb
                st.subheader("Таблица лидеров")
                st.dataframe(lb)

                summ = predictor.fit_summary()
                st.session_state["fit_summary"] = summ

                if not lb.empty:
                    best_model = lb.iloc[0]["model"]
                    best_score = lb.iloc[0]["score_val"]
                    st.session_state["best_model_name"] = best_model
                    st.session_state["best_model_score"] = best_score
                    st.info(f"Лучшая модель: {best_model}, score_val={best_score:.4f}")

                with st.expander("Резюме обучения"):
                    st.text(summ)

                # Важность признаков
                feature_importance = predictor.feature_importance(df2) # Данные обучения используются для важности признаков
                st.session_state["feature_importance"] = feature_importance
                st.subheader("Важность признаков")
                st.dataframe(feature_importance)


                save_model_metadata(
                    tgt_col, problem_type_val, eval_key,
                    fill_method_val, group_cols_val, # Групповые колонки удалены из интерфейса
                    presets_val, chosen_models_val
                )

            except Exception as ex:
                st.error(f"Ошибка во время обучения: {ex}")

    # ========== 6) Прогноз ==========
    st.sidebar.header("6. Прогноз")
    if st.sidebar.button("Сделать прогноз", key="predict_btn"):
        predictor = st.session_state.get("predictor")
        if predictor is None:
            st.warning("Сначала обучите модель или загрузите уже существующую!")
        elif tgt_col == "<нет>":
            st.error("Пожалуйста, выберите целевую колонку в разделе '2. Настройка колонок'!")
        else:
            df_predict = st.session_state.get("df_predict")


            if df_predict is None: # df_predict теперь обязателен
                st.error("Файл для прогнозирования обязателен. Пожалуйста, загрузите файл данных для прогнозирования.")
            else:
                try:

                    st.subheader("Прогноз на данных для прогнозирования")
                    df_pred = df_predict.copy()


                    df_pred = fill_missing_values(
                        df_pred,
                        st.session_state.get("fill_method_key", "None")
                    )


                    st.session_state["df_predict"] = df_pred


                    predictions = predict_tabular(predictor, df_pred)
                    st.session_state["predictions"] = predictions

                    st.subheader("Предсказанные значения (первые строки)")
                    # Объединяем данные для прогнозирования с **только колонкой предсказаний**
                    prediction_col_name = predictions.columns[0] # Предполагаем, что колонка предсказаний - первая (и единственная)
                    output_df = pd.concat([df_predict.reset_index(drop=True), predictions.reset_index(drop=True)[[prediction_col_name]]], axis=1) # Объединяем только колонку предсказаний
                    st.dataframe(output_df.head()) # Отображаем объединенный датафрейм

                    # Важность признаков после прогноза, если есть
                    feature_importance = st.session_state.get("feature_importance")
                    if feature_importance is not None:
                        with st.expander("Важность признаков (Сохраненная)"): # Выводим сохраненную важность признаков после прогноза
                            st.dataframe(feature_importance)


                    best_name = st.session_state.get("best_model_name", None)
                    best_score = st.session_state.get("best_model_score", None)
                    if best_name is not None:
                        st.info(f"Лучшая модель при обучении была: {best_name}, score_val={best_score:.4f}")

                except Exception as ex:
                    st.error(f"Ошибка прогноза: {ex}")

    # ========== 7) Сохранение результатов (Excel) ==========
    st.sidebar.header("7. Сохранение результатов")
    save_path = st.sidebar.text_input("Имя файла Excel", "results.xlsx", key="save_path_key")
    if st.sidebar.button("Сохранить результаты в Excel", key="save_btn"):
        try:
            df_predict = st.session_state.get("df_predict") # Только df_predict теперь
            lb = st.session_state.get("leaderboard")
            preds = st.session_state.get("predictions")
            feature_importance = st.session_state.get("feature_importance") # Важность признаков

            import openpyxl
            from openpyxl.utils import get_column_letter

            with pd.ExcelWriter(save_path, engine="openpyxl") as writer:

                if df_predict is not None: # Сохранение df_predict с предсказаниями
                    output_df = pd.concat([df_predict.reset_index(drop=True), preds.reset_index(drop=True)], axis=1)
                    output_df.to_excel(writer, sheet_name="РезультатыПрогноза", index=False)
                if lb is not None:
                    lb.to_excel(writer, sheet_name="ТаблицаЛидеров", index=False)
                if feature_importance is not None: # Сохранение важности признаков
                    feature_importance.to_excel(writer, sheet_name="ВажностьПризнаков", index=True)


                if lb is not None and not lb.empty:
                    workbook = writer.book
                    sheet = writer.sheets["ТаблицаЛидеров"]
                    best_idx = lb.iloc[0].name
                    best_model_name = lb.iloc[0]["model"]
                    best_score = lb.iloc[0]["score_val"]

                    fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                    row_excel = best_idx + 2
                    for col_idx in range(1, lb.shape[1] + 1):
                        cell = sheet.cell(row=row_excel, column=col_idx)
                        cell.fill = fill_green

                    explanation_row = lb.shape[0] + 3
                    explanation = (
                        f"Лучшая модель: {best_model_name}\n"
                        f"Причина: минимальный score_val = {best_score:.4f}"
                    )
                    sheet.cell(row=explanation_row, column=1).value = explanation

            st.success(f"Результаты сохранены в {save_path}")
        except Exception as ex:
            st.error(f"Ошибка сохранения результатов: {ex}")

    # ========== 8) Логи приложения ==========
    st.sidebar.header("8. Логи приложения")
    if st.sidebar.button("Показать логи", key="show_logs_btn"):
        logs_ = read_logs()
        st.subheader("Логи")
        st.text(logs_)

    # ========== 9) Загрузка моделей и логов ==========
    st.sidebar.header("9. Загрузка моделей и логов")
    if st.sidebar.button("Download AutogluonModels Content", key="download_model_and_logs"):
        if not os.path.exists("AutogluonModels"):
            st.error("Папка 'AutogluonModels' не найдена. Сначала обучите модель.")
        else:
            import zipfile
            import io
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk("AutogluonModels"):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start="AutogluonModels")
                        zipf.write(file_path, arcname=arcname)

            zip_buf.seek(0)
            st.download_button(
                label="Скачать архив (Модели и логи)",
                data=zip_buf,
                file_name="AutogluonModels.zip",
                mime="application/zip"
            )
            st.info("Содержимое папки AutogluonModels архивировано.")


if __name__ == "__main__":
    main()