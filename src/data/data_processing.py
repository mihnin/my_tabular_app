import pandas as pd
import logging
import streamlit as st
from pathlib import Path


def load_data(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """
    Загружает данные из CSV или Excel файла с проверкой и обработкой ошибок.
    """
    if not uploaded_file:
        logging.error("Попытка загрузки без выбора файла")
        raise ValueError("Ошибка: Файл не выбран!")

    file_ext = Path(uploaded_file.name).suffix.lower()
    logging.info(f"Начало загрузки файла: {uploaded_file.name}")

    try:
        if file_ext == '.csv':
            with st.spinner("Чтение CSV файла..."):
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        elif file_ext in ('.xls', '.xlsx'):
            with st.spinner("Чтение Excel файла..."):
                df = pd.read_excel(uploaded_file)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")

        if df.empty:
            logging.warning(f"Файл {uploaded_file.name} загружен, но DataFrame оказался пустым.")
            raise ValueError(f"Файл '{uploaded_file.name}' загружен, но не содержит данных или данные не распознаны. Проверьте содержимое файла.")

        logging.info(f"Успешно загружено {len(df)} строк из файла: {uploaded_file.name}")
        return df

    except pd.errors.ParserError as e:
        logging.error(f"Ошибка парсинга файла: {uploaded_file.name}. Ошибка: {str(e)}")
        raise ValueError(f"Ошибка чтения файла '{uploaded_file.name}': {e}")
    except Exception as e:
        logging.error(f"Критическая ошибка при загрузке файла: {uploaded_file.name}. Ошибка: {str(e)}")
        raise ValueError(f"Ошибка загрузки файла '{uploaded_file.name}': {str(e)}")


def show_dataset_stats(df: pd.DataFrame):
    """
    Отображает простую статистику DataFrame: describe и количество пропусков.
    """
    st.write("**Основная статистика для числовых столбцов**:")
    numerical_df = df.select_dtypes(include=[float, int])
    if not numerical_df.empty:
        st.write(numerical_df.describe())
    else:
        st.info("Нет числовых столбцов для отображения статистики.")

    st.write("**Количество пропусков (NaN) по столбцам:**")
    missing_info = df.isnull().sum()
    if not missing_info.empty:
        st.write(missing_info)
    else:
        st.info("Пропуски в данных не найдены.")

