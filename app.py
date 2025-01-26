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

# Import data processing, feature engineering, and prediction functions
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
    """Loads YAML config (METRICS_DICT, AG_MODELS)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file {path} not found.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    metrics_dict = data.get("metrics_dict", {})
    ag_models = data.get("ag_models", {})
    presets_list = data.get("presets_list", []) # Added presets list from config
    return metrics_dict, ag_models, presets_list


METRICS_DICT, AG_MODELS, PRESETS_LIST = load_config(CONFIG_PATH)


def save_model_metadata(tgt_col, problem_type, eval_metric, fill_method_val, group_cols_fill_val,
                       presets, chosen_models):
    """Saves all settings (columns, problem_type, metric, etc.) to JSON."""
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
    """Loads saved settings from model_info.json if available."""
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
    """Loads a pre-trained TabularPredictor if available in MODEL_DIR."""
    if not os.path.exists(MODEL_DIR):
        return
    try:
        loaded_predictor = TabularPredictor.load(MODEL_DIR)
        st.session_state["predictor"] = loaded_predictor
        st.info(f"Loaded previously trained model from {MODEL_DIR}")

        meta = load_model_metadata()
        if meta:
            st.session_state["tgt_col_key"] = meta.get("tgt_col", "<нет>")
            st.session_state["problem_type_key"] = meta.get("problem_type", "auto")
            st.session_state["eval_metric_key"] = meta.get("eval_metric", "auto")
            st.session_state["fill_method_key"] = meta.get("fill_method_val", "None")
            st.session_state["group_cols_for_fill_key"] = meta.get("group_cols_fill_val", [])
            st.session_state["presets_key"] = meta.get("presets", "medium_quality")
            st.session_state["models_key"] = meta.get("chosen_models", ["* (all)"])

            st.info("Settings (columns, problem type, metric, etc.) restored from model_info.json")
    except Exception as e:
        st.warning(f"Failed to automatically load model from {MODEL_DIR}. Error: {e}")


def main():
    setup_logger()
    logging.info("=== Starting Streamlit Tabular App (main) ===")

    if "predictor" not in st.session_state or st.session_state["predictor"] is None:
        try_load_existing_model()

    pages = ["Главная", "Help"]
    choice = st.sidebar.selectbox("Navigation", pages, key="page_choice")

    if choice == "Help":
        show_help_page()
        return

    st.title("AutoGluon Tabular App")

    # Initialize session_state keys
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
    if "feature_importance" not in st.session_state: # для feature importance
        st.session_state["feature_importance"] = None

    if "best_model_name" not in st.session_state:
        st.session_state["best_model_name"] = None
    if "best_model_score" not in st.session_state:
        st.session_state["best_model_score"] = None

    # ========== 1) Data Upload ==========
    st.sidebar.header("1. Upload Data")
    train_file = st.sidebar.file_uploader("Train Data (Required)", type=["csv", "xls", "xlsx"], key="train_file_uploader")
    predict_file = st.sidebar.file_uploader("Prediction Data (Required)", type=["csv", "xls", "xlsx"], key="predict_file_uploader") # Required now

    if st.sidebar.button("Load Data", key="load_data_btn"):
        if not train_file:
            st.error("Train file is required!")
        elif not predict_file: # Check for predict_file too
            st.error("Prediction file is required!")
        else:
            try:
                df_train = load_data(train_file)
                st.session_state["df"] = df_train
                st.success("Train file loaded successfully!")
                st.dataframe(df_train.head())

                st.subheader("Train Data Statistics")
                show_dataset_stats(df_train)

                df_predict = load_data(predict_file) # Prediction data is required now
                st.session_state["df_predict"] = df_predict
                st.success("Prediction file loaded successfully!")
                st.dataframe(df_predict.head())

                st.subheader("Prediction Data Statistics")
                show_dataset_stats(df_predict)

            except Exception as e:
                st.error(f"Error loading data: {e}")

    # ========== 2) Column Configuration ==========
    st.sidebar.header("2. Column Configuration")
    df_current = st.session_state["df"]
    if df_current is not None:
        all_cols = list(df_current.columns)
    else:
        all_cols = []

    tgt_stored = st.session_state.get("tgt_col_key", "<нет>")
    if tgt_stored not in ["<нет>"] + all_cols:
        st.session_state["tgt_col_key"] = "<нет>"

    tgt_col = st.sidebar.selectbox("Target Column", ["<нет>"] + all_cols, key="tgt_col_key")

    problem_type_options = ["auto", "binary", "multiclass", "regression"]
    problem_type = st.sidebar.selectbox("Problem Type", problem_type_options, index=0, key="problem_type_key")

    eval_metric_options = ["auto"] + list(METRICS_DICT.keys())
    eval_metric = st.sidebar.selectbox("Evaluation Metric", eval_metric_options, index=0, key="eval_metric_key")


    # ========== 3) Missing Value Handling ==========
    st.sidebar.header("3. Missing Value Handling")
    fill_options = ["None", "Constant=0", "Mean", "Median", "Mode"] # Removed Group Mean, Forward Fill as less relevant for tabular
    fill_method = st.sidebar.selectbox("Missing Value Fill Method", fill_options, key="fill_method_key")
    group_cols_for_fill = [] # Grouping less relevant for general tabular, removed from UI

    # ========== 4) Model & Training Settings ==========
    st.sidebar.header("4. Model & Training Settings")

    model_keys = list(AG_MODELS.keys())
    model_choices = ["* (all)"] + model_keys
    chosen_models = st.sidebar.multiselect(
        "AutoGluon Models",
        model_choices,
        default=st.session_state.get("models_key", ["* (all)"]),
        key="models_key"
    )

    presets = st.sidebar.selectbox("Presets", PRESETS_LIST,
                                   index=PRESETS_LIST.index(st.session_state.get("presets_key", "medium_quality")),
                                   key="presets_key")

    time_limit = st.sidebar.number_input("Training Time Limit (seconds)", 10, 36000, 60, key="time_limit_key")


    # ========== 5) Model Training ==========
    st.sidebar.header("5. Train Model")
    if st.sidebar.button("Train Model", key="fit_model_btn"):
        df_train = st.session_state.get("df")
        if df_train is None:
            st.warning("Please upload Train Data first!")
        elif tgt_col == "<нет>":
            st.error("Please select a Target Column!")
        else:
            try:
                shutil.rmtree("AutogluonModels", ignore_errors=True)

                fill_method_val = st.session_state.get("fill_method_key", "None")
                group_cols_val = st.session_state.get("group_cols_for_fill_key", []) # Not used in UI anymore
                chosen_metric_val = st.session_state.get("eval_metric_key")
                chosen_models_val = st.session_state.get("models_key")
                presets_val = st.session_state.get("presets_key", "medium_quality")
                t_limit = st.session_state.get("time_limit_key", 60)
                problem_type_val = st.session_state.get("problem_type_key")


                df2 = df_train.copy()
                df2 = fill_missing_values(df2, fill_method_val) # Group cols removed

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

                st.info("Training model...")
                predictor.fit(
                    train_data=df2,
                    time_limit=t_limit,
                    presets=presets_val,
                    hyperparameters=hyperparameters
                )

                st.session_state["predictor"] = predictor
                st.success("Model trained successfully!")

                lb = predictor.leaderboard(df2)
                st.session_state["leaderboard"] = lb
                st.subheader("Leaderboard")
                st.dataframe(lb)

                summ = predictor.fit_summary()
                st.session_state["fit_summary"] = summ

                if not lb.empty:
                    best_model = lb.iloc[0]["model"]
                    best_score = lb.iloc[0]["score_val"]
                    st.session_state["best_model_name"] = best_model
                    st.session_state["best_model_score"] = best_score
                    st.info(f"Best model: {best_model}, score_val={best_score:.4f}")

                with st.expander("Fit Summary"):
                    st.text(summ)

                # Feature Importance
                feature_importance = predictor.feature_importance(df2) # Train data used for feature importance
                st.session_state["feature_importance"] = feature_importance
                st.subheader("Feature Importance")
                st.dataframe(feature_importance)


                save_model_metadata(
                    tgt_col, problem_type_val, eval_key,
                    fill_method_val, group_cols_val, # Group cols removed from UI
                    presets_val, chosen_models_val
                )

            except Exception as ex:
                st.error(f"Error during training: {ex}")

    # ========== 6) Prediction ==========
    st.sidebar.header("6. Prediction")
    if st.sidebar.button("Make Predictions", key="predict_btn"):
        predictor = st.session_state.get("predictor")
        if predictor is None:
            st.warning("Please train a model first or load an existing one!")
        elif tgt_col == "<нет>":
            st.error("Please select Target Column in Column Configuration!")
        else:
            df_predict = st.session_state.get("df_predict")


            if df_predict is None: # df_predict is now required
                st.error("Prediction data is required. Please upload Prediction Data file.")
            else:
                try:

                    st.subheader("Predictions on Prediction Data")
                    df_pred = df_predict.copy()


                    df_pred = fill_missing_values(
                        df_pred,
                        st.session_state.get("fill_method_key", "None")
                    )


                    st.session_state["df_predict"] = df_pred


                    predictions = predict_tabular(predictor, df_pred)
                    st.session_state["predictions"] = predictions

                    st.subheader("Predicted Values (First Rows)")
                    # Объединяем Prediction Data с предсказаниями
                    output_df = pd.concat([df_predict.reset_index(drop=True), predictions.reset_index(drop=True)], axis=1)
                    st.dataframe(output_df.head()) # Display combined dataframe


                    best_name = st.session_state.get("best_model_name", None)
                    best_score = st.session_state.get("best_model_score", None)
                    if best_name is not None:
                        st.info(f"Best model during training: {best_name}, score_val={best_score:.4f}")

                except Exception as ex:
                    st.error(f"Prediction Error: {ex}")

    # ========== 7) Save Results (Excel) ==========
    st.sidebar.header("7. Save Results")
    save_path = st.sidebar.text_input("Excel File Name", "results.xlsx", key="save_path_key")
    if st.sidebar.button("Save Results to Excel", key="save_btn"):
        try:
            df_predict = st.session_state.get("df_predict") # Only df_predict now
            lb = st.session_state.get("leaderboard")
            preds = st.session_state.get("predictions")
            feature_importance = st.session_state.get("feature_importance") # Feature importance

            import openpyxl
            from openpyxl.utils import get_column_letter

            with pd.ExcelWriter(save_path, engine="openpyxl") as writer:

                if df_predict is not None: # Save df_predict with predictions
                    output_df = pd.concat([df_predict.reset_index(drop=True), preds.reset_index(drop=True)], axis=1)
                    output_df.to_excel(writer, sheet_name="PredictionResults", index=False)
                if lb is not None:
                    lb.to_excel(writer, sheet_name="Leaderboard", index=False)
                if feature_importance is not None: # Save feature importance
                    feature_importance.to_excel(writer, sheet_name="FeatureImportance", index=True)


                if lb is not None and not lb.empty:
                    workbook = writer.book
                    sheet = writer.sheets["Leaderboard"]
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
                        f"Best model: {best_model_name}\n"
                        f"Reason: minimal score_val = {best_score:.4f}"
                    )
                    sheet.cell(row=explanation_row, column=1).value = explanation

            st.success(f"Results saved to {save_path}")
        except Exception as ex:
            st.error(f"Error saving results: {ex}")

    # ========== 8) Application Logs ==========
    st.sidebar.header("8. Application Logs")
    if st.sidebar.button("Show Logs", key="show_logs_btn"):
        logs_ = read_logs()
        st.subheader("Logs")
        st.text(logs_)

    # ========== 9) Download Models and Logs ==========
    st.sidebar.header("9. Download Models & Logs")
    if st.sidebar.button("Download AutogluonModels Content", key="download_model_and_logs"):
        if not os.path.exists("AutogluonModels"):
            st.error("Folder 'AutogluonModels' not found. Train a model first.")
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
                label="Download Archive (Models & Logs)",
                data=zip_buf,
                file_name="AutogluonModels.zip",
                mime="application/zip"
            )
            st.info("AutogluonModels folder content archived.")


if __name__ == "__main__":
    main()