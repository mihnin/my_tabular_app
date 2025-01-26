from autogluon.tabular import TabularPredictor
import pandas as pd

def predict_tabular(predictor: TabularPredictor, data: pd.DataFrame) -> pd.DataFrame:
    """
    Делает прогнозы, используя обученный TabularPredictor.

    Аргументы:
        predictor: Обученный объект TabularPredictor.
        data: Pandas DataFrame для прогнозирования.

    Возвращает:
        Pandas DataFrame с предсказаниями.
    """
    predictions = predictor.predict(data)
    if isinstance(predictions, pd.Series): # <---- Проверка на Series
        predictions = predictions.to_frame(name='prediction') # Преобразуем Series в DataFrame с именем 'prediction'
    return predictions