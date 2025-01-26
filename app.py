import streamlit as st
import plotly.express as px
import pandas as pd
import logging
import shutil
import yaml
import os
import json
import io
import zipfile

from autogluon.tabular import TabularPredictor
from openpyxl.styles import PatternFill

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
    read_logs,
    LOG_FILE  # Импортируем LOG_FILE для доступа к имени файла лога
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
    logging.info(f"Конфигурация загружена из: {path}")
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
    logging.info(f"Метаданные модели сохранены в: {path_json}")


def load_model_metadata():
    """Загружает сохраненные настройки из model_info.json, если доступно."""
    path_json = os.path.join(MODEL_DIR, MODEL_INFO_FILE)
    if not os.path.exists(path_json):
        logging.info(f"Файл метаданных модели не найден: {path_json}")
        return None
    try:
        with open(path_json, "r", encoding="utf-8") as f:
            info = json.load(f)
        logging.info(f"Метаданные модели загружены из: {path_json}")
        return info
    except Exception as e:
        logging.error(f"Ошибка при загрузке метаданных модели из {path_json}: {e}", exc_info=True)
        return None

def try_load_existing_model():
    """Загружает предварительно обученный TabularPredictor, если доступен в MODEL_DIR."""
    if not os.path.exists(MODEL_DIR):
        logging.info(f"Папка модели не найдена: {MODEL_DIR}, загрузка существующей модели пропущена.")
        return
    try:
        loaded_predictor = TabularPredictor.load(MODEL_DIR)
        st.session_state["predictor"] = loaded_predictor
        st.info(f"Загружена ранее обученная модель из {MODEL_DIR}")
        logging.info(f"Успешно загружена ранее обученная модель из: {MODEL_DIR}")

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
            logging.info("Настройки модели восстановлены из model_info.json")
    except Exception as e:
        st.warning(f"Не удалось автоматически загрузить модель из {MODEL_DIR}. Ошибка: {e}")
        logging.error(f"Ошибка при автоматической загрузке модели из {MODEL_DIR}: {e}", exc_info=True)

def display_fit_summary(fit_summary):
    """Отображает резюме обучения в структурированном виде."""
    if fit_summary is None:
        st.warning("Резюме обучения отсутствует.")
        return

    st.subheader("Общая информация")
    st.write(f"- Тип проблемы: {fit_summary.get('problem_type', 'Н/Д')}")
    st.write(f"- Метрика оценки: {fit_summary.get('eval_metric', 'Н/Д')}")
    st.write(f"- Лучшая модель: {fit_summary.get('model_best', 'Н/Д')}")
    st.write(f"- Количество классов: {fit_summary.get('num_classes', 'Н/Д')}")
    st.write(f"- Количество фолдов для бэггинга: {fit_summary.get('num_bag_folds', 'Н/Д')}")
    st.write(f"- Максимальный уровень стекинга: {fit_summary.get('max_stack_level', 'Н/Д')}")

    st.subheader("Производительность моделей")
    model_performance = fit_summary.get('model_performance', {})
    if model_performance:
        df_performance = pd.DataFrame.from_dict(model_performance, orient='index', columns=['Score'])
        st.dataframe(df_performance.sort_values(by='Score', ascending=False))
    else:
        st.write("Информация о производительности моделей отсутствует.")

    st.subheader("Время обучения моделей")
    model_fit_times = fit_summary.get('model_fit_times', {})
    if model_fit_times:
        df_fit_times = pd.DataFrame.from_dict(model_fit_times, orient='index', columns=['Время обучения (сек)'])
        st.dataframe(df_fit_times.sort_values(by='Время обучения (сек)', ascending=True))
    else:
        st.write("Информация о времени обучения моделей отсутствует.")

    st.subheader("Время прогнозирования моделей")
    model_pred_times = fit_summary.get('model_pred_times', {})
    if model_pred_times:
        df_pred_times = pd.DataFrame.from_dict(model_pred_times, orient='index', columns=['Время прогнозирования (сек)'])
        st.dataframe(df_pred_times.sort_values(by='Время прогнозирования (сек)', ascending=True))
    else:
        st.write("Информация о времени прогнозирования моделей отсутствует.")

    st.subheader("Гиперпараметры моделей")
    model_hyperparams = fit_summary.get('model_hyperparams', {})
    if model_hyperparams:
        st.json(model_hyperparams) # Отображение гиперпараметров в виде JSON, можно улучшить форматирование при необходимости
    else:
        st.write("Информация о гиперпараметрах моделей отсутствует.")


def main():
    setup_logger()
    logging.info("=== Запуск Streamlit Tabular App (main) ===")

    if "predictor" not in st.session_state or st.session_state["predictor"] is None:
        try_load_existing_model()

    pages = ["Главная", "Help"]
    choice = st.sidebar.selectbox("Навигация", pages, key="page_choice")
    logging.info(f"Выбрана страница: {choice}")

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
        logging.info("Нажата кнопка 'Загрузить данные'")
        logging.info(f"  - Тренировочный файл загружен: {train_file is not None}")
        logging.info(f"  - Файл прогноза загружен: {predict_file is not None}")
        if not train_file:
            st.error("Тренировочный файл обязателен!")
            logging.warning("Тренировочный файл не выбран.")
        elif not predict_file: # Проверка на наличие predict_file
            st.error("Файл для прогнозирования обязателен!")
            logging.warning("Файл для прогнозирования не выбран.")
        else:
            try:
                logging.info(f"Загрузка тренировочных данных из файла: {train_file.name}")
                df_train = load_data(train_file)
                st.session_state["df"] = df_train
                st.success("Тренировочный файл успешно загружен!")
                st.dataframe(df_train.head())

                st.subheader("Статистика тренировочных данных")
                show_dataset_stats(df_train)

                logging.info(f"Загрузка данных для прогнозирования из файла: {predict_file.name}")
                df_predict = load_data(predict_file) # Данные для прогнозирования теперь обязательны
                st.session_state["df_predict"] = df_predict
                st.success("Файл для прогнозирования успешно загружен!")
                st.dataframe(df_predict.head())

                st.subheader("Статистика данных для прогнозирования")
                show_dataset_stats(df_predict)
                logging.info("Данные успешно загружены и статистика отображена.")

            except Exception as e:
                st.error(f"Ошибка загрузки данных: {e}")
                logging.error(f"Ошибка при загрузке данных: {e}", exc_info=True)

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
    logging.info(f"Выбрана целевая колонка: {tgt_col}")

    problem_type_options = ["auto", "binary", "multiclass", "regression"]
    problem_type = st.sidebar.selectbox("Тип задачи", problem_type_options, index=0, key="problem_type_key")
    logging.info(f"Выбран тип задачи: {problem_type}")

    eval_metric_options = ["auto"] + list(METRICS_DICT.keys())
    eval_metric = st.sidebar.selectbox("Метрика оценки", eval_metric_options, index=0, key="eval_metric_key")
    logging.info(f"Выбрана метрика оценки: {eval_metric}")


    # ========== 3) Обработка пропущенных значений ==========
    st.sidebar.header("3. Обработка пропущенных значений")
    fill_options = ["None", "Constant=0", "Mean", "Median", "Mode"] # Удалены Group Mean, Forward Fill как менее релевантные для табличных данных
    fill_method = st.sidebar.selectbox("Метод заполнения пропущенных значений", fill_options, key="fill_method_key")
    logging.info(f"Выбран метод заполнения пропусков: {fill_method}")
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
    logging.info(f"Выбранные модели AutoGluon: {chosen_models}")

    presets = st.sidebar.selectbox("Пресеты", PRESETS_LIST,
                                   index=PRESETS_LIST.index(st.session_state.get("presets_key", "medium_quality")),
                                   key="presets_key")
    logging.info(f"Выбран пресет: {presets}")

    time_limit = st.sidebar.number_input("Лимит времени обучения (секунды)", 10, 36000, 60, key="time_limit_key")
    logging.info(f"Установлен лимит времени обучения: {time_limit} секунд")


    # ========== 5) Обучение модели ==========
    st.sidebar.header("5. Обучение модели")
    auto_predict_save = st.sidebar.checkbox("Прогноз и сохранение после обучения", value=False, key="auto_predict_save_checkbox") # Чекбокс для авто прогноза и сохранения
    logging.info(f"Чекбокс 'Прогноз и сохранение после обучения' установлен: {auto_predict_save}")
    if st.sidebar.button("Обучить модель", key="fit_model_btn"):
        logging.info("Нажата кнопка 'Обучить модель'")
        logging.info(f"  - Автоматический прогноз и сохранение после обучения: {auto_predict_save}")
        logging.info(f"  - Целевая колонка: {tgt_col}")
        logging.info(f"  - Тип задачи: {problem_type}")
        logging.info(f"  - Метрика оценки: {eval_metric}")
        logging.info(f"  - Метод заполнения пропусков: {fill_method}")
        logging.info(f"  - Выбранные модели: {chosen_models}")
        logging.info(f"  - Пресет: {presets}")
        logging.info(f"  - Лимит времени: {time_limit}")

        df_train = st.session_state.get("df")
        if df_train is None:
            st.warning("Пожалуйста, загрузите тренировочные данные сначала!")
            logging.warning("Обучение модели: тренировочные данные не загружены.")
        elif tgt_col == "<нет>":
            st.error("Пожалуйста, выберите целевую колонку!")
            logging.warning("Обучение модели: целевая колонка не выбрана.")
        else:
            try:
                shutil.rmtree("AutogluonModels", ignore_errors=True)
                logging.info("Обучение модели: предыдущие модели удалены из AutogluonModels.")

                fill_method_val = st.session_state.get("fill_method_key", "None")
                group_cols_val = st.session_state.get("group_cols_for_fill_key", []) # Не используется в интерфейсе больше
                chosen_metric_val = st.session_state.get("eval_metric_key")
                chosen_models_val = st.session_state.get("models_key")
                presets_val = st.session_state.get("presets_key", "medium_quality")
                t_limit = st.session_state.get("time_limit_key", 60)
                problem_type_val = st.session_state.get("problem_type_key")

                logging.info(f"Параметры обучения: Целевая колонка={tgt_col}, Тип задачи={problem_type_val}, Метрика={chosen_metric_val}, Метод заполнения пропусков={fill_method_val}, Пресеты={presets_val}, Лимит времени={t_limit}, Выбранные модели={chosen_models_val}")


                df2 = df_train.copy()
                df2 = fill_missing_values(df2, fill_method_val) # Групповые колонки удалены
                logging.info("Пропущенные значения заполнены.")

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
                logging.info("Начало обучения модели...")
                predictor.fit(
                    train_data=df2,
                    time_limit=t_limit,
                    presets=presets_val,
                    hyperparameters=hyperparameters
                )

                st.session_state["predictor"] = predictor
                st.success("Модель успешно обучена!")
                logging.info("Модель успешно обучена.")

                lb = predictor.leaderboard(df2)
                st.session_state["leaderboard"] = lb
                st.subheader("Таблица лидеров")
                st.dataframe(lb)
                logging.info("Таблица лидеров отображена.")

                summ = predictor.fit_summary()
                st.session_state["fit_summary"] = summ

                if not lb.empty:
                    best_model = lb.iloc[0]["model"]
                    best_score = lb.iloc[0]["score_val"]
                    st.session_state["best_model_name"] = best_model
                    st.session_state["best_model_score"] = best_score
                    st.info(f"Лучшая модель: {best_model}, score_val={best_score:.4f}")
                    logging.info(f"Лучшая модель: {best_model}, score_val={best_score:.4f}")

                with st.expander("Резюме обучения"):
                    display_fit_summary(summ) # Используем улучшенное отображение резюме
                logging.info("Резюме обучения отображено.")

                # Важность признаков
                feature_importance = predictor.feature_importance(df2) # Данные обучения используются для важности признаков
                st.session_state["feature_importance"] = feature_importance
                st.subheader("Важность признаков")
                st.dataframe(feature_importance)
                logging.info("Важность признаков отображена.")


                save_model_metadata(
                    tgt_col, problem_type_val, eval_key,
                    fill_method_val, group_cols_val, # Групповые колонки удалены из интерфейса
                    presets_val, chosen_models_val
                )

                if auto_predict_save: # Автоматический запуск прогноза и сохранения если чекбокс выбран
                    st.info("Автоматически запускаем прогноз и сохранение результатов...")
                    logging.info("Автоматически запускаем прогноз и сохранение результатов, так как чекбокс установлен.")
                    # Запускаем прогноз
                    predictor = st.session_state.get("predictor")
                    df_predict = st.session_state.get("df_predict")

                    if predictor is not None and df_predict is not None:
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
                            # Обработка случая, когда predictions является Series
                            if isinstance(predictions, pd.Series):
                                prediction_col_name = 'prediction'  # Даем столбцу предсказаний имя по умолчанию
                                predictions = predictions.to_frame(name=prediction_col_name) # Преобразуем Series в DataFrame
                            else: # predictions это DataFrame
                                prediction_col_name = predictions.columns[0] # Предполагаем, что колонка предсказаний - первая (и единственная)
                            # Объединяем данные для прогнозирования с **только колонкой предсказаний**
                            output_df = pd.concat([df_predict.reset_index(drop=True), predictions.reset_index(drop=True)[[prediction_col_name]]], axis=1) # Объединяем только колонку предсказаний
                            st.dataframe(output_df.head())
                            logging.info("Автоматический прогноз успешно выполнен и отображен.")


                        except Exception as ex_pred:
                            st.error(f"Ошибка прогноза при автоматическом запуске: {ex_pred}")
                            logging.error(f"Ошибка прогноза при автоматическом запуске: {ex_pred}", exc_info=True)
                        else: # Если прогноз успешен, запускаем сохранение
                            try:
                                save_path = st.session_state.get("save_path_key", "results.xlsx")
                                df_predict_to_save = st.session_state.get("df_predict") # Только df_predict теперь
                                lb_to_save = st.session_state.get("leaderboard")
                                preds_to_save = st.session_state.get("predictions")
                                feature_importance_to_save = st.session_state.get("feature_importance") # Важность признаков

                                with pd.ExcelWriter(save_path, engine="openpyxl") as writer:

                                    if df_predict_to_save is not None: # Сохранение df_predict с предсказаниями
                                        output_df_save = pd.concat([df_predict_to_save.reset_index(drop=True), preds_to_save.reset_index(drop=True)], axis=1)
                                        output_df_save.to_excel(writer, sheet_name="РезультатыПрогноза", index=False)
                                    if lb_to_save is not None:
                                        lb_to_save.to_excel(writer, sheet_name="ТаблицаЛидеров", index=False)
                                    if feature_importance_to_save is not None: # Сохранение важности признаков
                                        feature_importance_to_save.to_excel(writer, sheet_name="ВажностьПризнаков", index=True)


                                    if lb_to_save is not None and not lb_to_save.empty:
                                        workbook = writer.book
                                        sheet = writer.sheets["ТаблицаЛидеров"]
                                        best_idx = lb_to_save.iloc[0].name
                                        best_model_name = lb_to_save.iloc[0]["model"]
                                        best_score = lb_to_save.iloc[0]["score_val"]

                                        fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                                        row_excel = best_idx + 2
                                        for col_idx in range(1, lb_to_save.shape[1] + 1):
                                            cell = sheet.cell(row=row_excel, column=col_idx)
                                            cell.fill = fill_green

                                        explanation_row = lb_to_save.shape[0] + 3
                                        explanation = (
                                            f"Лучшая модель: {best_model_name}\n"
                                            f"Причина: минимальный score_val = {best_score:.4f}"
                                        )
                                        sheet.cell(row=explanation_row, column=1).value = explanation

                                st.success(f"Результаты автоматически сохранены в {save_path}")
                                logging.info(f"Результаты автоматически сохранены в Excel файл: {save_path}")
                            except Exception as ex_save:
                                st.error(f"Ошибка сохранения результатов при автоматическом запуске: {ex_save}")
                                logging.error(f"Ошибка сохранения результатов при автоматическом запуске: {ex_save}", exc_info=True)

            except Exception as ex:
                st.error(f"Ошибка во время обучения: {ex}")
                logging.error(f"Ошибка во время обучения: {ex}", exc_info=True)

    # ========== 6) Прогноз ==========
    st.sidebar.header("6. Прогноз")
    if st.sidebar.button("Сделать прогноз", key="predict_btn"):
        logging.info("Нажата кнопка 'Сделать прогноз'")
        predictor = st.session_state.get("predictor")
        if predictor is None:
            st.warning("Сначала обучите модель или загрузите уже существующую!")
            logging.warning("Прогноз: модель не обучена или не загружена.")
        elif tgt_col == "<нет>":
            st.error("Пожалуйста, выберите целевую колонку в разделе '2. Настройка колонок'!")
            logging.warning("Прогноз: целевая колонка не выбрана.")
        else:
            df_predict = st.session_state.get("df_predict")


            if df_predict is None: # df_predict теперь обязателен
                st.error("Файл для прогнозирования обязателен. Пожалуйста, загрузите файл данных для прогнозирования.")
                logging.warning("Прогноз: файл для прогнозирования не загружен.")
            else:
                try:

                    st.subheader("Прогноз на данных для прогнозирования")
                    df_pred = df_predict.copy()

                    df_pred = fill_missing_values(
                        df_pred,
                        st.session_state.get("fill_method_key", "None")
                    )
                    logging.info("Пропущенные значения в данных для прогноза заполнены.")

                    st.session_state["df_predict"] = df_pred

                    logging.info("Запуск прогноза...")
                    predictions = predict_tabular(predictor, df_pred)
                    st.session_state["predictions"] = predictions
                    logging.info("Прогноз успешно выполнен.")

                    st.subheader("Предсказанные значения (первые строки)")
                    # Обработка случая, когда predictions является Series
                    if isinstance(predictions, pd.Series):
                        prediction_col_name = 'prediction'  # Даем столбцу предсказаний имя по умолчанию
                        predictions = predictions.to_frame(name=prediction_col_name) # Преобразуем Series в DataFrame
                    else: # predictions это DataFrame
                        prediction_col_name = predictions.columns[0] # Предполагаем, что колонка предсказаний - первая (и единственная)
                    # Объединяем данные для прогнозирования с **только колонкой предсказаний**
                    output_df = pd.concat([df_predict.reset_index(drop=True), predictions.reset_index(drop=True)[[prediction_col_name]]], axis=1) # Объединяем только колонку предсказаний
                    st.dataframe(output_df.head()) # Отображаем объединенный датафрейм
                    logging.info("Предсказанные значения отображены.")

                    # Важность признаков после прогноза, если есть
                    feature_importance = st.session_state.get("feature_importance")
                    if feature_importance is not None:
                        with st.expander("Важность признаков (Сохраненная)"): # Выводим сохраненную важность признаков после прогноза
                            st.dataframe(feature_importance)
                            logging.info("Важность признаков (сохраненная) отображена в выпадающем списке.")


                    best_name = st.session_state.get("best_model_name", None)
                    best_score = st.session_state.get("best_model_score", None)
                    if best_name is not None:
                        st.info(f"Лучшая модель при обучении была: {best_name}, score_val={best_score:.4f}")
                        logging.info(f"Информация о лучшей модели отображена: {best_name}, score_val={best_score:.4f}")

                except Exception as ex:
                    st.error(f"Ошибка прогноза: {ex}")
                    logging.error(f"Ошибка прогноза: {ex}", exc_info=True)

    # ========== 7) Сохранение результатов (Excel) ==========
    st.sidebar.header("7. Сохранение результатов")
    save_path = st.sidebar.text_input("Имя файла Excel", "results.xlsx", key="save_path_key")
    logging.info(f"Установлено имя файла для сохранения результатов: {save_path}")
    if st.sidebar.button("Сохранить результаты в Excel", key="save_btn"):
        logging.info("Нажата кнопка 'Сохранить результаты в Excel'")
        logging.info(f"  - Имя файла для сохранения: {save_path}")
        try:
            df_predict = st.session_state.get("df_predict") # Только df_predict теперь
            lb = st.session_state.get("leaderboard")
            preds = st.session_state.get("predictions")
            feature_importance = st.session_state.get("feature_importance") # Важность признаков

            with pd.ExcelWriter(save_path, engine="openpyxl") as writer:

                if df_predict is not None: # Сохранение df_predict с предсказаниями
                    output_df = pd.concat([df_predict.reset_index(drop=True), preds.reset_index(drop=True)], axis=1)
                    output_df.to_excel(writer, sheet_name="РезультатыПрогноза", index=False)
                    logging.info("Лист 'РезультатыПрогноза' сохранен в Excel.")
                if lb is not None:
                    lb.to_excel(writer, sheet_name="ТаблицаЛидеров", index=False)
                    logging.info("Лист 'ТаблицаЛидеров' сохранен в Excel.")
                if feature_importance is not None: # Сохранение важности признаков
                    feature_importance.to_excel(writer, sheet_name="ВажностьПризнаков", index=True)
                    logging.info("Лист 'ВажностьПризнаков' сохранен в Excel.")


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
                    logging.info("Форматирование и пояснение для лучшей модели добавлены в лист 'ТаблицаЛидеров'.")

            st.success(f"Результаты сохранены в {save_path}")
            logging.info(f"Результаты успешно сохранены в Excel файл: {save_path}")
        except Exception as ex:
            st.error(f"Ошибка сохранения результатов: {ex}")
            logging.error(f"Ошибка сохранения результатов в Excel: {ex}", exc_info=True)

    # ========== 8) Логи приложения ==========
    st.sidebar.header("8. Логи приложения")
    if st.sidebar.button("Показать логи", key="show_logs_btn"):
        logging.info("Нажата кнопка 'Показать логи'")
        logs_ = read_logs()
        st.subheader("Логи")
        st.text(logs_)
        logging.info("Логи приложения отображены на экране.")

    if st.sidebar.button("Скачать логи в текстовый файл", key="download_logs_btn"):
        logging.info("Нажата кнопка 'Скачать логи в текстовый файл'")
        try:
            with open(LOG_FILE, "r", encoding='utf-8') as f:
                log_content = f.read()
            st.download_button(
                label="Скачать логи",
                data=log_content,
                file_name="app_logs.txt",
                mime="text/plain"
            )
            logging.info("Кнопка скачивания логов отображена.")
        except Exception as e:
            st.error(f"Ошибка при подготовке логов к скачиванию: {e}")
            logging.error(f"Ошибка при подготовке логов к скачиванию: {e}", exc_info=True)


    # ========== 9) Загрузка моделей и логов ==========
    st.sidebar.header("9. Загрузка моделей и логов")
    if st.sidebar.button("Download AutogluonModels Content", key="download_model_and_logs"):
        logging.info("Нажата кнопка 'Download AutogluonModels Content'")
        if not os.path.exists("AutogluonModels"):
            st.error("Папка 'AutogluonModels' не найдена. Сначала обучите модель.")
            logging.warning("Папка 'AutogluonModels' не найдена, невозможно скачивание.")
        else:
            try:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk("AutogluonModels"):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, start="AutogluonModels")
                            zipf.write(file_path, arcname=arcname)
                zip_buffer.seek(0)

                st.download_button(
                    label="Скачать архив (Модели и логи)",
                    data=zip_buffer,
                    file_name="AutogluonModels.zip",
                    mime="application/zip"
                )
                st.info("Содержимое папки AutogluonModels архивировано и готово к скачиванию.")
                logging.info("Папка 'AutogluonModels' архивирована и предложена для скачивания.")

            except Exception as e:
                st.error(f"Ошибка при архивации и подготовке к скачиванию: {e}")
                logging.error(f"Ошибка при архивации папки 'AutogluonModels': {e}", exc_info=True)


if __name__ == "__main__":
    main()
