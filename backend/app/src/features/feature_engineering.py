import pandas as pd
import streamlit as st
import logging


def fill_missing_values(df: pd.DataFrame, method: str = "None") -> pd.DataFrame:
    """
    Заполняет пропущенные значения в числовых столбцах выбранным методом,
    а в нечисловых (категориальных) всегда модой.
      - "Constant=0": NaN -> 0 (числовые)
      - "Mean": заполнение средним значением (числовые)
      - "Median": заполнение медианой (числовые)
      - "Mode": заполнение модой (числовые)
      - "None": без изменений (числовые)
    """
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns

    # Всегда заполняем нечисловые модой
    for col in categorical_cols:
        mode = df[col].mode()
        if not mode.empty:
            df[col] = df[col].fillna(mode.iloc[0])

    if method == "None":
        return df
    elif method == "Constant=0":
        df[numeric_cols] = df[numeric_cols].fillna(0)
    elif method == "Mean":
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
    elif method == "Median":
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    elif method == "Mode":
        df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mode().iloc[0])
    
    return df

