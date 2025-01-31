# app.py
import streamlit as st
import plotly.express as px
import pandas as pd
import shutil
import yaml
import os
import json
import io
import zipfile

from autogluon.tabular import TabularPredictor
from openpyxl.styles import PatternFill

# Локальные модули
from src.data.data_processing import load_data, show_dataset_stats
from src.features.feature_engineering import fill_missing_values
from src.models.prediction import predict_tabular

# Теперь берём функции для логов из utils:
from src.utils.utils import (
    setup_logger,
    read_logs,
    log_info,
    log_warning,
    log_error,
    log_debug,
    LOG_FILE
)
from src.help_page import show_help_page

CONFIG_PATH = "config/config.yaml"
MODEL_DIR = "AutogluonModels/TabularModel"
MODEL_INFO_FILE = "model_info.json"

def load_config(path: str):
    if not os.path.exists(path):
        log_error(f"Файл конфигурации {path} не найден.")
        raise FileNotFoundError(f"Файл конфигурации {path} не найден.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    metrics_dict = data.get("metrics_dict", {})
    ag_models = data.get("ag_models", {})
    presets_list = data.get("presets_list", [])
    log_info(f"Конфигурация загружена из: {path}")
    return metrics_dict, ag_models, presets_list

METRICS_DICT, AG_MODELS, PRESETS_LIST = load_config(CONFIG_PATH)


def save_model_metadata(col_target, problem_type, eval_metric,
                        fill_method, group_cols, presets, chosen_models):
    os.makedirs(MODEL_DIR, exist_ok=True)
    info_dict = {
        "целевая_колонка": col_target,
        "тип_задачи": problem_type,
        "метрика_оценки": eval_metric,
        "метод_заполнения_пропусков": fill_method,
        "группировочные_колонки_для_заполнения": group_cols,
        "пресеты": presets,
        "выбранные_модели": chosen_models,
    }
    path_json = os.path.join(MODEL_DIR, MODEL_INFO_FILE)
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(info_dict, f, ensure_ascii=False, indent=2)
    log_info(f"Настройки модели сохранены: {path_json}")

def load_model_metadata():
    path_json = os.path.join(MODEL_DIR, MODEL_INFO_FILE)
    if not os.path.exists(path_json):
        log_info("model_info.json не найден, пропускаем автозагрузку.")
        return None
    try:
        with open(path_json, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error(f"Ошибка чтения model_info.json: {e}")
        return None

def try_load_existing_model():
    if not os.path.exists(MODEL_DIR):
        log_info("Папка модели не найдена, пропускаем автозагрузку.")
        return
    try:
        loaded_predictor = TabularPredictor.load(MODEL_DIR)
        st.session_state["predictor"] = loaded_predictor
        st.info(f"Автозагрузка модели из {MODEL_DIR}")

        meta = load_model_metadata()
        if meta:
            st.session_state["tgt_col_key"] = meta.get("целевая_колонка", "<нет>")
            st.session_state["problem_type_key"] = meta.get("тип_задачи", "auto")
            st.session_state["eval_metric_key"] = meta.get("метрика_оценки", "auto")
            st.session_state["fill_method_key"] = meta.get("метод_заполнения_пропусков", "None")
            st.session_state["group_cols_for_fill_key"] = meta.get("группировочные_колонки_для_заполнения", [])
            st.session_state["presets_key"] = meta.get("пресеты", "medium_quality")
            st.session_state["models_key"] = meta.get("выбранные_модели", ["* (all)"])
            st.info("Настройки восстановлены из model_info.json")
    except Exception as e:
        st.warning(f"Не удалось загрузить модель: {e}")
        log_warning(f"Не удалось загрузить модель: {e}")

def display_fit_summary(fit_summary):
    if fit_summary is None:
        st.warning("fit_summary отсутствует.")
        return

    st.subheader("Общая информация")
    st.write(f"- Тип задачи: {fit_summary.get('problem_type','N/A')}")
    st.write(f"- Метрика: {fit_summary.get('eval_metric','N/A')}")
    st.write(f"- Лучшая модель: {fit_summary.get('model_best','N/A')}")

    st.subheader("Производительность моделей")
    perf = fit_summary.get("model_performance", {})
    if perf:
        df_ = pd.DataFrame.from_dict(perf, orient="index", columns=["Score"])
        st.dataframe(df_.sort_values(by="Score", ascending=False))
    else:
        st.write("Нет информации.")

    st.subheader("Время обучения моделей")
    ft = fit_summary.get("model_fit_times", {})
    if ft:
        df_ = pd.DataFrame.from_dict(ft, orient="index", columns=["FitTime"])
        st.dataframe(df_.sort_values(by="FitTime", ascending=True))
    else:
        st.write("Нет данных о времени обучения.")

    st.subheader("Время предсказаний")
    pt = fit_summary.get("model_pred_times", {})
    if pt:
        df_ = pd.DataFrame.from_dict(pt, orient="index", columns=["PredTime"])
        st.dataframe(df_.sort_values(by="PredTime", ascending=True))
    else:
        st.write("Нет данных о времени предсказания.")

    st.subheader("Гиперпараметры моделей")
    mhp = fit_summary.get("model_hyperparams", {})
    if mhp:
        st.json(mhp)
    else:
        st.write("Нет гиперпараметров.")

def extract_ensemble_info(predictor, best_model_name: str):
    if not best_model_name.startswith("WeightedEnsemble"):
        return None
    info = predictor.info()
    model_info_all = info.get("model_info", {})
    best_info = model_info_all.get(best_model_name, {})
    child_info = best_info.get("children_info", {})
    weights = child_info.get("child_weights", [])
    children = child_info.get("child_model_names", [])
    if not weights or not children:
        return None
    data = []
    for c, w in zip(children, weights):
        data.append({"Model": c, "Weight": w})
    return pd.DataFrame(data)

def main():
    # Используем логгер (по умолчанию INFO, можно debug=True при нужде)
    setup_logger(debug=False)
    log_info("=== Запуск приложения (Tabular) в режиме INFO ===")

    # Попробуем загрузить модель
    if "predictor" not in st.session_state or st.session_state["predictor"] is None:
        try_load_existing_model()

    pages = ["Главная", "Help"]
    choice = st.sidebar.selectbox("Навигация", pages)

    if choice == "Help":
        show_help_page()
        return

    st.title("Бизнес-приложение для прогнозирования табличных данных. Версия 1.0")

    # Инициализация
    for key_ in ["df","df_predict","predictor","leaderboard","predictions","fit_summary","feature_importance","ensemble_info"]:
        if key_ not in st.session_state:
            st.session_state[key_] = None

    # (1) Загрузка
    st.sidebar.header("1. Загрузка данных")
    train_file = st.sidebar.file_uploader("Train-файл", type=["csv","xls","xlsx"])
    predict_file = st.sidebar.file_uploader("Прогноз-файл", type=["csv","xls","xlsx"])

    if st.sidebar.button("Загрузить"):
        if not train_file:
            st.error("Train обязателен!")
            log_warning("Пользователь не выбрал Train-файл.")
        elif not predict_file:
            st.error("Прогноз-файл обязателен!")
            log_warning("Пользователь не выбрал файл для прогнозов.")
        else:
            try:
                df_train = load_data(train_file)
                st.session_state["df"] = df_train
                st.success("Train загружен!")
                st.dataframe(df_train.head())

                st.subheader("Статистика Train")
                show_dataset_stats(df_train)
                log_info(f"Train-файл {train_file.name} успешно загружен ({len(df_train)} строк).")

                df_predict = load_data(predict_file)
                st.session_state["df_predict"] = df_predict
                st.success("Файл для прогноза загружен!")
                st.dataframe(df_predict.head())

                st.subheader("Статистика (прогноз)")
                show_dataset_stats(df_predict)
                log_info(f"Файл для прогноза {predict_file.name} успешно загружен ({len(df_predict)} строк).")

            except Exception as e:
                st.error(f"Ошибка загрузки: {e}")
                log_error(f"Ошибка загрузки: {e}")

    # (2) Настройка колонок
    st.sidebar.header("2. Настройка колонок")
    df_cur = st.session_state["df"]
    all_cols = list(df_cur.columns) if df_cur is not None else []

    if "tgt_col_key" not in st.session_state:
        st.session_state["tgt_col_key"] = "<нет>"
    else:
        if st.session_state["tgt_col_key"] not in ["<нет>"] + all_cols:
            st.session_state["tgt_col_key"] = "<нет>"

    tgt_col = st.sidebar.selectbox("Целевая колонка", ["<нет>"]+all_cols, key="tgt_col_key")
    log_info(f"Выбрана целевая колонка: {tgt_col}")

    if "problem_type_key" not in st.session_state:
        st.session_state["problem_type_key"] = "auto"
    problem_options = ["auto","binary","multiclass","regression"]
    problem_type = st.sidebar.selectbox("Тип задачи", problem_options, key="problem_type_key")
    log_info(f"Выбран тип задачи: {problem_type}")

    if "eval_metric_key" not in st.session_state:
        st.session_state["eval_metric_key"] = "auto"
    eval_metric_list = ["auto"] + list(METRICS_DICT.keys())
    eval_metric = st.sidebar.selectbox("Метрика", eval_metric_list, key="eval_metric_key")
    log_info(f"Выбрана метрика: {eval_metric}")

    # (3) Пропуски
    st.sidebar.header("3. Обработка пропусков")
    fill_opts = ["None","Constant=0","Mean","Median","Mode"]
    if "fill_method_key" not in st.session_state:
        st.session_state["fill_method_key"] = "None"
    fill_method = st.sidebar.selectbox("Заполнение пропусков", fill_opts, key="fill_method_key")
    log_info(f"Метод заполнения: {fill_method}")

    group_cols_for_fill = []

    # (4) Настройки модели
    st.sidebar.header("4. Настройки модели")
    model_keys_list = list(AG_MODELS.keys())
    model_choices = ["* (all)"] + model_keys_list
    if "models_key" not in st.session_state:
        st.session_state["models_key"] = ["* (all)"]
    chosen_models = st.sidebar.multiselect("Модели AutoGluon", model_choices,
                                           default=st.session_state["models_key"],
                                           key="models_key")
    log_info(f"Выбраны модели: {chosen_models}")

    if "presets_key" not in st.session_state:
        st.session_state["presets_key"] = "medium_quality"
    presets = st.sidebar.selectbox("Presets", PRESETS_LIST,
                                   index=PRESETS_LIST.index(st.session_state["presets_key"]) if st.session_state["presets_key"] in PRESETS_LIST else 0,
                                   key="presets_key")
    log_info(f"Выбран пресет: {presets}")

    if "time_limit_key" not in st.session_state:
        st.session_state["time_limit_key"] = 60
    time_limit = st.sidebar.number_input("Time limit (sec)", 10, 36000, st.session_state["time_limit_key"], key="time_limit_key")
    log_info(f"Лимит времени: {time_limit} сек")

    # (5) Обучение
    st.sidebar.header("5. Обучение")
    if "auto_predict_save_checkbox" not in st.session_state:
        st.session_state["auto_predict_save_checkbox"] = False
    auto_predict_save = st.sidebar.checkbox("Авто-прогноз и сохранение", value=False, key="auto_predict_save_checkbox")
    log_info(f"Флаг автопрогноза: {auto_predict_save}")

    if st.sidebar.button("Обучить модель"):
        df_tr = st.session_state.get("df")
        if df_tr is None:
            st.warning("Train не загружен!")
            log_warning("Попытка обучения без Train.")
        elif tgt_col == "<нет>":
            st.error("Целевая колонка не выбрана!")
            log_warning("Обучение невозможно: tgt_col='<нет>'")
        else:
            try:
                log_info("Удаляем старые модели из AutogluonModels...")
                shutil.rmtree("AutogluonModels", ignore_errors=True)

                fill_val = fill_method
                chosen_metric_val = eval_metric if eval_metric!="auto" else None
                log_info(f"Начинаем обучение (metric={chosen_metric_val}, time_limit={time_limit}, presets={presets}, models={chosen_models})")

                df_ready = df_tr.copy()
                df_ready = fill_missing_values(df_ready, fill_val)
                all_models_opt = "* (all)"
                if (len(chosen_models)==1 and chosen_models[0]==all_models_opt) or (len(chosen_models)==0):
                    hyperparams = None
                else:
                    no_star = [m for m in chosen_models if m!=all_models_opt]
                    hyperparams = {m: {} for m in no_star}

                predictor = TabularPredictor(
                    label=tgt_col,
                    problem_type=problem_type if problem_type!="auto" else None,
                    eval_metric=chosen_metric_val,
                    path=MODEL_DIR
                ).fit(
                    train_data=df_ready,
                    time_limit=time_limit,
                    presets=presets,
                    hyperparameters=hyperparams
                )

                st.session_state["predictor"] = predictor
                st.success("Модель обучена!")
                log_info("Модель успешно обучена.")

                lb = predictor.leaderboard(df_ready)
                st.session_state["leaderboard"] = lb
                st.subheader("Лидерборд")
                st.dataframe(lb)
                log_info(f"Лидерборд:\n{lb}")

                fsumm = predictor.fit_summary()
                st.session_state["fit_summary"] = fsumm
                with st.expander("Fit Summary"):
                    display_fit_summary(fsumm)

                fi = predictor.feature_importance(df_ready)
                st.session_state["feature_importance"] = fi
                st.subheader("Важность признаков")
                st.dataframe(fi)
                log_info(f"Feature Importance:\n{fi}")

                if not lb.empty:
                    best_model = lb.iloc[0]["model"]
                    best_score = lb.iloc[0]["score_val"]
                    st.info(f"Лучшая модель: {best_model}, score={best_score:.4f}")
                    log_info(f"Лучшая модель: {best_model} (score={best_score:.4f})")

                    ens_df = extract_ensemble_info(predictor, best_model)
                    if ens_df is not None:
                        st.session_state["ensemble_info"] = ens_df
                        st.write("### Состав WeightedEnsemble")
                        st.dataframe(ens_df)
                        log_info(f"Ансамбль WeightedEnsemble:\n{ens_df}")

                save_model_metadata(
                    col_target=tgt_col,
                    problem_type=problem_type,
                    eval_metric=chosen_metric_val,
                    fill_method=fill_val,
                    group_cols=group_cols_for_fill,
                    presets=presets,
                    chosen_models=chosen_models
                )

                # Автопрогноз
                if auto_predict_save:
                    st.info("Автоматический прогноз + Excel для скачивания...")
                    df_fore = st.session_state.get("df_predict")
                    if df_fore is None:
                        st.warning("Нет данных для прогноза!")
                        log_warning("Автопрогноз невозможен: df_predict=None")
                    else:
                        try:
                            dff_ = df_fore.copy()
                            dff_ = fill_missing_values(dff_, fill_val)
                            preds = predictor.predict(dff_)
                            if isinstance(preds, pd.Series):
                                preds = preds.to_frame("prediction")
                            out_df = pd.concat([dff_.reset_index(drop=True), preds.reset_index(drop=True)], axis=1)
                            st.dataframe(out_df.head())

                            excel_buf = io.BytesIO()
                            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                                out_df.to_excel(writer, sheet_name="РезультатыПрогноза", index=False)
                                lb.to_excel(writer, sheet_name="ТаблицаЛидеров", index=False)
                                if not lb.empty:
                                    sheet_lb = writer.sheets["ТаблицаЛидеров"]
                                    bidx = lb.iloc[0].name
                                    fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                                    row_excel = bidx + 2
                                    for col_idx in range(1, lb.shape[1]+1):
                                        cell = sheet_lb.cell(row=row_excel, column=col_idx)
                                        cell.fill = fill_green
                                fi.to_excel(writer, sheet_name="ВажностьПризнаков", index=True)
                                if st.session_state["ensemble_info"] is not None:
                                    st.session_state["ensemble_info"].to_excel(writer, sheet_name="EnsembleInfo", index=False)

                            excel_buf.seek(0)
                            st.download_button(
                                label="Скачать Excel (авто)",
                                data=excel_buf.getvalue(),
                                file_name="results.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            st.success("Файл Excel можно скачать.")
                            log_info("Автопрогноз: Excel сформирован, пользователь может скачать.")

                        except Exception as ax:
                            st.error(f"Ошибка автопрогноза: {ax}")
                            log_error(f"Ошибка автопрогноза: {ax}")

            except Exception as ex_:
                st.error(f"Ошибка обучения: {ex_}")
                log_error(f"Ошибка обучения: {ex_}")

    # (6) Прогноз вручную
    st.sidebar.header("6. Прогноз вручную")
    if st.sidebar.button("Сделать прогноз"):
        predictor = st.session_state.get("predictor")
        if predictor is None:
            st.warning("Сначала обучите модель!")
            log_warning("Нельзя прогнозировать: predictor=None.")
        elif tgt_col == "<нет>":
            st.error("Целевая колонка не выбрана.")
            log_warning("Нельзя прогнозировать: tgt_col='<нет>'.")
        else:
            df_fore = st.session_state.get("df_predict")
            if df_fore is None:
                st.error("Нет файла для прогноза!")
                log_warning("Нельзя прогнозировать: df_predict=None.")
            else:
                try:
                    fmethod = st.session_state["fill_method_key"]
                    df_fore_ = df_fore.copy()
                    df_fore_ = fill_missing_values(df_fore_, fmethod)
                    preds = predictor.predict(df_fore_)
                    if isinstance(preds, pd.Series):
                        preds = preds.to_frame("prediction")
                    out_ = pd.concat([df_fore_.reset_index(drop=True), preds.reset_index(drop=True)], axis=1)
                    st.session_state["predictions"] = out_
                    st.subheader("Предсказанные значения (первые строки)")
                    st.dataframe(out_.head())
                    log_info(f"Ручной прогноз выполнен, первые строки:\n{out_.head(5)}")

                    if st.session_state["ensemble_info"] is not None:
                        st.write("Состав WeightedEnsemble:")
                        st.dataframe(st.session_state["ensemble_info"])

                except Exception as xp:
                    st.error(f"Ошибка прогноза: {xp}")
                    log_error(f"Ошибка прогноза: {xp}")

    # (7) Сохранение (CSV/Excel)
    st.sidebar.header("7. Сохранение результатов")
    if st.sidebar.button("Сохранить в CSV"):
        final_preds = st.session_state.get("predictions")
        if final_preds is None:
            st.warning("Сделайте прогноз (predictions=None).")
            log_warning("Нельзя сохранить CSV: нет 'predictions'.")
        else:
            csv_data = final_preds.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="Скачать CSV",
                data=csv_data,
                file_name="results.csv",
                mime="text/csv"
            )
            log_info("Пользователь может скачать results.csv")

    if st.sidebar.button("Сохранить в Excel"):
        final_preds = st.session_state.get("predictions")
        lb = st.session_state.get("leaderboard")
        fi = st.session_state.get("feature_importance")
        en_df = st.session_state.get("ensemble_info")
        if final_preds is None:
            st.warning("Сделайте прогноз (predictions=None).")
            log_warning("Нельзя сохранить Excel: нет 'predictions'.")
        else:
            xbuf = io.BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                final_preds.to_excel(writer, sheet_name="РезультатыПрогноза", index=False)
                if lb is not None:
                    lb.to_excel(writer, sheet_name="ТаблицаЛидеров", index=False)
                    if not lb.empty:
                        sheet_lb = writer.sheets["ТаблицаЛидеров"]
                        best_idx = lb.iloc[0].name
                        fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                        row_excel = best_idx + 2
                        for col_idx in range(1, lb.shape[1]+1):
                            cell = sheet_lb.cell(row=row_excel, column=col_idx)
                            cell.fill = fill_green
                if fi is not None:
                    fi.to_excel(writer, sheet_name="ВажностьПризнаков", index=True)
                if en_df is not None:
                    en_df.to_excel(writer, sheet_name="EnsembleInfo", index=False)

            xbuf.seek(0)
            st.download_button(
                label="Скачать Excel",
                data=xbuf.getvalue(),
                file_name="results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            log_info("Пользователь может скачать results.xlsx (ручной)")

    # (8) Логи приложения
    st.sidebar.header("8. Логи приложения")
    if st.sidebar.button("Показать логи"):
        logs_ = read_logs()
        st.subheader("Лог-файл (app.log)")
        st.text(logs_)

    if st.sidebar.button("Скачать логи"):
        logs_ = read_logs()
        st.download_button(
            label="Скачать app.log",
            data=logs_,
            file_name="app.log",
            mime="text/plain"
        )

    clear_input = st.sidebar.text_input("Очистить логи (delete):")
    if st.sidebar.button("Очистить логи"):
        if clear_input.strip().lower() == "delete":
            # Закрываем все хендлеры
            logger = logging.getLogger()
            for h in logger.handlers[:]:
                if hasattr(h, 'baseFilename') and os.path.abspath(h.baseFilename) == os.path.abspath(LOG_FILE):
                    h.close()
                    logger.removeHandler(h)
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.warning("Логи удалены!")
            else:
                st.info("Нет файла логов.")
            with open(LOG_FILE, 'w', encoding='utf-8'):
                pass
            fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
            formatter = ...
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            log_info("Создан новый log-файл (после очистки).")
        else:
            st.warning("Неверное слово, логи не очищены.")

    # (9) Скачать модели + логи
    st.sidebar.header("9. Скачать модели + логи")
    if st.sidebar.button("Скачать архив (модели+логи)"):
        if not os.path.exists("AutogluonModels"):
            st.error("Папка AutogluonModels не найдена.")
            log_warning("Нет AutogluonModels => архив скачать нельзя.")
        else:
            try:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk("AutogluonModels"):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, start="AutogluonModels")
                            zf.write(full_path, arcname)
                    if os.path.exists(LOG_FILE):
                        zf.write(LOG_FILE, arcname="app.log")

                zip_buf.seek(0)
                st.download_button(
                    label="Скачать models_and_logs.zip",
                    data=zip_buf.getvalue(),
                    file_name="models_and_logs.zip",
                    mime="application/zip"
                )
                log_info("Пользователь может скачать models_and_logs.zip")
            except Exception as e_:
                st.error(f"Ошибка архивации: {e_}")
                log_error(f"Ошибка архивации: {e_}")

if __name__ == "__main__":
    main()

