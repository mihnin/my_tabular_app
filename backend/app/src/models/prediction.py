from autogluon.tabular import TabularPredictor
import pandas as pd

def predict_tabular(predictor: TabularPredictor, data: pd.DataFrame) -> pd.DataFrame:
    """
    Makes predictions using a trained TabularPredictor.

    Args:
        predictor: Trained TabularPredictor object.
        data: Pandas DataFrame for prediction.

    Returns:
        Pandas DataFrame with predictions.
    """
    predictions = predictor.predict(data)
    return predictions