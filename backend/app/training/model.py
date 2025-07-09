from typing import List, Optional, Union
from pydantic import BaseModel, Field


class TrainingParameters(BaseModel):
    target_column: str = Field(..., description="Название целевой колонки для прогнозирования.")
    fill_missing_method: Optional[str] = Field("None", description="Метод заполнения пропущенных значений (например, 'mean', 'median', 'None').")
    evaluation_metric: Optional[str] = Field(None, description="Метрика оценки для AutoGluon (например, 'accuracy', 'f1', 'rmse').")
    models_to_train: Optional[Union[str, List[str], None]] = Field(None, description="Конкретные модели для обучения. Если None или пустой список, обучаются все доступные модели. Если '*', обучаются все доступные модели.")
    autogluon_preset: Optional[str] = Field("medium_quality", description="Пресет AutoGluon (например, 'medium_quality', 'high_quality', 'best_quality').")
    problem_type: Optional[str] = Field("auto", description="Тип задачи (например, 'auto', 'binary', 'multiclass', 'regression').")
    training_time_limit: Optional[int] = Field(None, description="Ограничение времени на обучение в секундах. Если None, то без ограничений.")
    download_table_name: Optional[str] = Field(None, description="Название таблицы из которой будет загружен датасет")
    upload_table_name: Optional[str] = Field(None, description="Название таблицы в которую будет загружен датасет")
    upload_table_schema: Optional[str] = Field(None, description="Схема для сохранения прогноза в БД")