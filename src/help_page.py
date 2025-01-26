import streamlit as st

def show_help_page():
    st.title("Help Page")
    st.markdown("""
## About this App

This Streamlit application uses AutoGluon-Tabular to train and deploy machine learning models for tabular data prediction. 
It allows you to easily upload your datasets, configure training parameters, train models, and make predictions without writing code.

## Navigation

- **Главная (Main):**  The main interface for uploading data, configuring training, training models, making predictions, and downloading results.
- **Help:** This page, providing information and guidance on using the application.

## Steps to Use the App

1.  **Upload Data:**
    -   **Train Data (Required):** Upload your training dataset in CSV, XLS, or XLSX format. This dataset will be used to train the AutoGluon model.
    -   **Prediction Data (Optional):** Upload a separate dataset for making predictions after training. If not provided, predictions will be made on the train dataset itself.

2.  **Column Configuration:**
    -   **Target Column:** Select the column in your dataset that you want to predict. This is the dependent variable.
    -   **Problem Type:** Choose the type of prediction task:
        -   **auto:** AutoGluon automatically infers the problem type (classification or regression).
        -   **binary:** Binary classification (two classes).
        -   **multiclass:** Multiclass classification (more than two classes).
        -   **regression:** Regression (predicting a continuous numerical value).
    -   **Evaluation Metric:** Select the metric to optimize for during training. 'auto' uses AutoGluon's default choice.

3.  **Missing Value Handling:**
    -   **Missing Value Fill Method:** Choose how to handle missing values in your dataset:
        -   **None:** Leave missing values as they are (not recommended unless your data has no missing values or models can handle them).
        -   **Constant=0:** Fill missing values with 0.
        -   **Mean:** Fill missing values with the mean of the column.
        -   **Median:** Fill missing values with the median of the column.
        -   **Mode:** Fill missing values with the mode (most frequent value) of the column.

4.  **Model & Training Settings:**
    -   **AutoGluon Models:** Select specific AutoGluon models to include in training, or choose '* (all)' to train all available models.
    -   **Presets:** Choose a preset configuration for training speed and quality:
        -   **fast_training:** Fastest training time, lowest accuracy.
        -   **medium_quality:**  Fast training time, ideal for initial prototyping.
        -   **high_quality:** Strong accuracy with fast inference speed.
        -   **best_quality:** Maximize accuracy, may increase training time.
    -   **Training Time Limit (seconds):** Specify the maximum time (in seconds) to spend training the model.

5.  **Train Model:**
    -   Click the "Train Model" button to start the AutoGluon training process with the configured settings.

6.  **Prediction:**
    -   Once the model is trained, click the "Make Predictions" button to generate predictions. If you uploaded a Prediction Data file, predictions will be made on that data; otherwise, predictions will be made on the Train Data.

7.  **Save Results:**
    -   **Excel File Name:** Enter the desired name for the Excel file to save the results.
    -   Click "Save Results to Excel" to download an Excel file containing:
        -   Train Data
        -   Prediction Data (if uploaded)
        -   Leaderboard of trained models
        -   Predictions

8.  **Application Logs:**
    -   Click "Show Logs" to view the application logs for debugging or monitoring.

9.  **Download Models & Logs:**
    -   Click "Download AutogluonModels Content" to download a ZIP archive containing the trained AutoGluon models and application logs. This is useful for deploying or archiving your trained model.

## Important Notes

-   **Data Requirements:** Ensure your data is in a tabular format (CSV, XLS, XLSX) and that you select the correct column configurations.
-   **Training Time:** Training time can vary significantly based on dataset size, complexity, and the chosen time limit and presets.
-   **Model Performance:** Model performance depends on the quality and characteristics of your data and the chosen training settings. Review the Leaderboard to understand model performance.
-   **File Paths:** Be aware of file paths when downloading models and logs.

For any issues or further questions, please refer to the AutoGluon documentation or community support.
    """)