import pandas as pd
import logging
import streamlit as st
from pathlib import Path

def load_data(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """Loads data from CSV/Excel file with validation and error handling."""
    if not uploaded_file:
        logging.error("Attempted load without file selection")
        raise ValueError("Error: No file selected!")

    file_ext = Path(uploaded_file.name).suffix.lower()
    logging.info(f"Starting file load: {uploaded_file.name}")

    try:
        if file_ext == '.csv':
            with st.spinner("Reading CSV file..."):
                df = pd.read_csv(uploaded_file)
        elif file_ext in ('.xls', '.xlsx'):
            with st.spinner("Reading Excel file..."):
                df = pd.read_excel(uploaded_file)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        logging.info(f"Successfully loaded {len(df)} rows")
        return df

    except pd.errors.ParserError as e:
        logging.error(f"Parsing error: {str(e)}")
        raise ValueError(f"Error reading file: {e}")
    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        raise ValueError(f"Error loading: {str(e)}")


def show_dataset_stats(df: pd.DataFrame):
    """Displays basic dataset statistics in Streamlit."""
    st.write("**Basic Statistics for Numerical Columns:**")
    st.write(df.describe(include=[float, int]))

    st.write("**Missing Value Counts per Column:**")
    missing_info = df.isnull().sum()
    st.write(missing_info)