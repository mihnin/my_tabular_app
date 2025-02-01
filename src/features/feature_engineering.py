import pandas as pd
import streamlit as st
import logging


def fill_missing_values(df: pd.DataFrame, method: str = "None") -> pd.DataFrame:
    """
    Заполняет пропущенные значения в числовых столбцах.
      - "Constant=0": NaN -> 0
      - "Mean": заполнение средним значением
      - "Median": заполнение медианой
      - "Mode": заполнение модой
      - "None": без изменений
    """
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns

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

