import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useData } from '../contexts/DataContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Button } from '@/components/ui/button.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Checkbox } from '@/components/ui/checkbox.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { 
  Settings, 
  Calendar, 
  Target, 
  Hash,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react'

// Метрики по задачам
const metricsByTask = {
  auto: [
    'accuracy', 'balanced_accuracy', 'roc_auc', 'f1', 'precision', 'recall', 'log_loss', 'average_precision',
    'root_mean_squared_error', 'mean_squared_error', 'mean_absolute_error', 'r2', 'pearsonr', 'spearmanr'
  ],
  binary: [
    'accuracy', 'balanced_accuracy', 'roc_auc', 'f1', 'precision', 'recall', 'log_loss', 'average_precision'
  ],
  multiclass: [
    'accuracy', 'balanced_accuracy', 'f1', 'precision', 'recall', 'log_loss'
  ],
  regression: [
    'root_mean_squared_error', 'mean_squared_error', 'mean_absolute_error', 'r2', 'pearsonr', 'spearmanr'
  ]
}

// Полный список метрик с описаниями + auto
const allMetricOptions = [
  { id: 'auto', label: 'auto', description: 'Автоматически выбрать метрику' },
  { id: 'accuracy', label: 'Accuracy', description: 'Доля правильных ответов' },
  { id: 'balanced_accuracy', label: 'Balanced Accuracy', description: 'Сбалансированная точность' },
  { id: 'roc_auc', label: 'ROC AUC', description: 'Площадь под ROC-кривой' },
  { id: 'f1', label: 'F1', description: 'F1-мера' },
  { id: 'precision', label: 'Precision', description: 'Точность' },
  { id: 'recall', label: 'Recall', description: 'Полнота' },
  { id: 'log_loss', label: 'Log Loss', description: 'Логарифмическая функция потерь' },
  { id: 'average_precision', label: 'Average Precision', description: 'Средняя точность' },
  { id: 'root_mean_squared_error', label: 'RMSE', description: 'Root Mean Squared Error' },
  { id: 'mean_squared_error', label: 'MSE', description: 'Mean Squared Error' },
  { id: 'mean_absolute_error', label: 'MAE', description: 'Mean Absolute Error' },
  { id: 'r2', label: 'R2', description: 'Коэффициент детерминации' },
  { id: 'pearsonr', label: 'PearsonR', description: 'Коэффициент корреляции Пирсона' },
  { id: 'spearmanr', label: 'SpearmanR', description: 'Коэффициент корреляции Спирмена' }
]

export default function ModelConfig() {
  const navigate = useNavigate()
  const { trainData, dataSource, selectedTable, updateTrainingConfig, trainingConfig } = useData()
  
  const [config, setConfig] = useState({
    targetColumn: 'none',
    missingValueMethod: 'mean', // По умолчанию mean
    selectedAutogluonModels: ['*'],
    selectedMetric: 'auto', // По умолчанию auto
    autogluonPreset: 'medium_quality',
    trainingTimeLimit: 60,
    taskType: 'auto'
  })

  const [selectedAutogluonModelToAdd, setSelectedAutogluonModelToAdd] = useState('none')

  // Инициализация конфигурации из сохраненного состояния
  useEffect(() => {
    if (trainingConfig) {
      setConfig(prev => ({
        ...trainingConfig,
        selectedMetric: trainingConfig.selectedMetric || 'auto'
      }))
    }
  }, []) // Загружаем только при монтировании компонента

  // Автосохранение конфигурации при каждом изменении
  useEffect(() => {
    // Избегаем сохранения при первой загрузке
    if (config.targetColumn) {
      updateTrainingConfig(config)
    }
  }, [config, updateTrainingConfig])

  // Получаем доступные колонки только из trainData
  const availableColumns = trainData && trainData.columns ? trainData.columns : []

  // Методы обработки пропусков из MissingValueHandler.vue
  const missingValueMethods = [
    { value: 'None', label: 'None (не заполнять)' },
    { value: 'constant=0', label: 'constant=0 (заменить на 0)' },
    { value: 'mean', label: 'mean (среднее)' },
    { value: 'median', label: 'median (медиана)' },
    { value: 'mode', label: 'mode (мода)' }
  ]

  // --- AutoGluon модели только из agModels ---
  const agModels = [
    { id: '*', label: 'Все модели', description: 'Использовать все доступные AutoGluon модели' },
    { id: 'CAT', label: 'CatBoost', description: 'CatBoost' },
    { id: 'GBM', label: 'LightGBM', description: 'LightGBM' },
    { id: 'RF', label: 'RandomForestGini', description: 'RandomForestGini' },
    { id: 'XT', label: 'ExtraTreesGini', description: 'ExtraTreesGini' },
    { id: 'XGB', label: 'XGBoost', description: 'XGBoost' },
    { id: 'FASTAI', label: 'NeuralNetFastAI', description: 'NeuralNetFastAI' },
    { id: 'NN_TORCH', label: 'PyTorchNN', description: 'PyTorchNN' },
    { id: 'LR', label: 'Linear scikit', description: 'Linear scikit' },
    { id: 'KNN', label: 'KNearestNeighbors', description: 'KNearestNeighbors' }
  ]

  const presetsList = [
    { id: 'medium_quality', label: 'medium_quality', description: '' },
    { id: 'high_quality', label: 'high_quality', description: '' },
    { id: 'best_quality', label: 'best_quality', description: '' },
    { id: 'good_quality', label: 'good_quality', description: '' },
    { id: 'optimize_for_deployment', label: 'optimize_for_deployment', description: '' },
    { id: 'experimental', label: 'experimental', description: '' }
  ]

  const handleConfigChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  const handleModelToggle = (modelId) => {
    const fieldName = 'selectedAutogluonModels'
    setConfig(prev => ({
      ...prev,
      [fieldName]: prev[fieldName].includes(modelId)
        ? prev[fieldName].filter(id => id !== modelId)
        : [...prev[fieldName], modelId]
    }))
  }

  const handleModelAdd = (modelId) => {
    if (modelId && modelId !== 'none') {
      const fieldName = 'selectedAutogluonModels'
      
      setConfig(prev => {
        const currentModels = prev[fieldName]
        
        // Если выбирают "Все модели"
        if (modelId === '*') {
          return { ...prev, [fieldName]: ['*'] }
        }
        
        // Если уже выбраны "Все модели", заменяем на конкретную модель
        if (currentModels.includes('*')) {
          return { ...prev, [fieldName]: [modelId] }
        }
        
        // Если модель уже выбрана, не добавляем
        if (currentModels.includes(modelId)) {
          return prev
        }
        
        // Добавляем модель к существующим
        return { ...prev, [fieldName]: [...currentModels, modelId] }
      })
      
      // Сбрасываем селектор
      setSelectedAutogluonModelToAdd('none')
    }
  }

  const handleModelRemove = (modelId) => {
    const fieldName = 'selectedAutogluonModels'
    setConfig(prev => ({
      ...prev,
      [fieldName]: prev[fieldName].filter(id => id !== modelId)
    }))
  }

  // Удаляю блок выбора ID-колонки (Select idColumn)
  // Удаляю блок статических признаков (staticFeatures, handleStaticFeatureAdd/Remove, availableStaticFeatures, и т.д.)

  // Доступные колонки для группировки (из статических признаков)
  const availableGroupingColumns = [] // Удалены статические признаки, поэтому группировка невозможна

  // Доступные модели для добавления
  const availableAutogluonModels = agModels.filter(model => !config.selectedAutogluonModels.includes(model.id))

  const isConfigValid = config.targetColumn && 
                       (config.selectedAutogluonModels.length > 0) && 
                       config.selectedMetric

  // Получить список метрик для выбранной задачи
  const getMetricOptions = () => {
    if (!config.taskType || config.taskType === 'none') {
      return allMetricOptions
    }
    const allowed = metricsByTask[config.taskType] || metricsByTask['auto']
    // always include 'auto' as first
    return [allMetricOptions[0], ...allMetricOptions.filter(m => allowed.includes(m.id))]
  }
  const metricOptions = getMetricOptions()

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">Конфигурация модели</h1>
        <p className="text-muted-foreground">
          Настройте параметры для обучения модели на табличных данных
        </p>
      </div>

      <div className="space-y-6">
        {/* Column Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="text-primary" size={20} />
              <span>Выбор колонок</span>
            </CardTitle>
            <CardDescription>
              Укажите колонки для целевой переменной и идентификатора
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="flex items-center space-x-2">
                  <Target size={16} className="text-primary" />
                  <span>Целевая переменная *</span>
                </Label>
                <Select value={config.targetColumn} onValueChange={(value) => handleConfigChange('targetColumn', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите целевую переменную" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none" disabled>Выберите целевую переменную</SelectItem>
                    {availableColumns.map(column => (
                      <SelectItem key={column} value={column}>{column}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="flex items-center space-x-2">
                  <span>Тип задачи *</span>
                </Label>
                <Select value={config.taskType || 'auto'} onValueChange={(value) => handleConfigChange('taskType', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите тип задачи" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">auto (автоопределение)</SelectItem>
                    <SelectItem value="binary">binary (бинарная классификация)</SelectItem>
                    <SelectItem value="multiclass">multiclass (мультиклассовая классификация)</SelectItem>
                    <SelectItem value="regression">regression (регрессия)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Удаляю блок выбора ID-колонки (Select idColumn) */}
            </div>

            {/* Статические признаки */}
            <div className="space-y-4">
              {/* Выбранные признаки */}
              {/* Удалены статические признаки, поэтому этот блок будет пуст */}

              {/* Селектор для добавления признаков */}
              {/* Удалены статические признаки, поэтому этот селектор будет пуст */}

              {/* Чекбокс для праздников */}
              {/* Удалены статические признаки, поэтому этот блок будет пуст */}
            </div>
          </CardContent>
        </Card>

        {/* Data Processing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="text-primary" size={20} />
              <span>Обработка данных</span>
            </CardTitle>
            <CardDescription>
              Настройте методы обработки пропусков
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Метод обработки пропусков</Label>
                <Select value={config.missingValueMethod || 'mean'} onValueChange={(value) => handleConfigChange('missingValueMethod', value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {missingValueMethods.map(method => (
                      <SelectItem key={method.value} value={method.value}>{method.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Группировочные колонки для Group mean */}
            {config.missingValueMethod === 'group_mean' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Колонки для группировки</Label>
                  <p className="text-sm text-muted-foreground">
                    Выберите колонки для вычисления среднего значения по группам
                  </p>
                </div>

                {/* Выбранные группировочные колонки */}
                {/* Удалены статические признаки, поэтому этот блок будет пуст */}

                {/* Селектор для добавления группировочных колонок */}
                {/* Удалены статические признаки, поэтому этот селектор будет пуст */}

                {/* Сообщение, если нет доступных статических признаков */}
                {/* Удалены статические признаки, поэтому этот блок будет пуст */}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Model Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="text-primary" size={20} />
              <span>Выбор моделей</span>
            </CardTitle>
            <CardDescription>
              Выберите модели для обучения и сравнения
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* AutoGluon Models */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-lg font-semibold text-foreground">AutoGluon модели</Label>
                <p className="text-sm text-muted-foreground">
                  Модели из библиотеки AutoGluon для табличных данных
                </p>
              </div>

              {/* Выбранные AutoGluon модели */}
              {config.selectedAutogluonModels.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {config.selectedAutogluonModels.map((modelId) => {
                    const model = agModels.find(m => m.id === modelId)
                    return (
                      <div key={modelId} className="flex items-center bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm">
                        <span>{model?.label || modelId}</span>
                        <button
                          onClick={() => handleModelRemove(modelId)}
                          className="ml-2 text-blue-500 hover:text-blue-700 font-bold"
                          type="button"
                        >
                          ×
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Селекторы для добавления AutoGluon моделей и пресета */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Добавить модель</Label>
                  <Select 
                    value={selectedAutogluonModelToAdd}
                    onValueChange={(value) => {
                      setSelectedAutogluonModelToAdd(value)
                      handleModelAdd(value)
                    }}
                    disabled={availableAutogluonModels.length === 0}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите модель для добавления" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Выберите модель</SelectItem>
                      {availableAutogluonModels.map(model => (
                        <SelectItem key={model.id} value={model.id}>{model.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>Пресет AutoGluon</Label>
                  <Select 
                    value={config.autogluonPreset} 
                    onValueChange={(value) => handleConfigChange('autogluonPreset', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите пресет">
                        {config.autogluonPreset ? presetsList.find(p => p.id === config.autogluonPreset)?.label : "Выберите пресет"}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {presetsList.map(preset => (
                        <SelectItem key={preset.id} value={preset.id}>
                          <div className="flex flex-col">
                            <span className="font-medium">{preset.label}</span>
                            <span className="text-xs text-muted-foreground">{preset.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Additional Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="text-primary" size={20} />
              <span>Дополнительные настройки</span>
            </CardTitle>
            <CardDescription>
              Настройки метрики качества и ограничения времени обучения
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Метрика оценки качества</Label>
                <Select 
                  value={config.selectedMetric} 
                  onValueChange={(value) => handleConfigChange('selectedMetric', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите метрику">
                      {config.selectedMetric ? metricOptions.find(m => m.id === config.selectedMetric)?.label : "Выберите метрику"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {metricOptions.map(metric => (
                      <SelectItem key={metric.id} value={metric.id}>
                        <div className="flex flex-col">
                          <span className="font-medium">{metric.label}</span>
                          <span className="text-xs text-muted-foreground">{metric.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Максимальное время обучения (секунды)</Label>
                <Input
                  type="number"
                  min="30"
                  max="3600"
                  value={config.trainingTimeLimit}
                  onChange={(e) => handleConfigChange('trainingTimeLimit', parseInt(e.target.value) || 60)}
                  placeholder="60"
                />
                <p className="text-xs text-muted-foreground">
                  Ограничение времени на обучение всех моделей (от 30 до 3600 секунд)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Configuration Summary */}
        {isConfigValid && (
          <Card className="bg-green-50 border-green-200">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-green-800">
                <Info className="text-green-600" size={20} />
                <span>Сводка конфигурации</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-green-700">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p><strong>Источник данных:</strong> {dataSource === 'file' ? 'Файл' : dataSource === 'database' ? `БД (${selectedTable})` : 'Не загружено'}</p>
                  <p><strong>Целевая переменная:</strong> {config.targetColumn}</p>
                  <p><strong>Тип задачи:</strong> {config.taskType}</p>
                </div>
                <div>
                  <p><strong>Метод обработки пропусков:</strong> {missingValueMethods.find(m => m.value === config.missingValueMethod)?.label}</p>
                  <p><strong>Выбрано AutoGluon моделей:</strong> {config.selectedAutogluonModels.length}</p>
                  <p><strong>Метрика качества:</strong> {allMetricOptions.find(m => m.id === config.selectedMetric)?.label}</p>
                  <p><strong>Время обучения:</strong> {config.trainingTimeLimit} секунд</p>
                  {trainData && trainData.rows && (
                    <p><strong>Строк данных:</strong> {trainData.rows.length}</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Action Buttons */}
        <div className="flex justify-between">
          <Button 
            variant="outline"
            onClick={() => navigate('/upload')}
          >
            Назад к загрузке данных
          </Button>
          <Button 
            className="bg-primary hover:bg-primary/90"
            disabled={!isConfigValid}
            onClick={() => {
              updateTrainingConfig(config)
              navigate('/training')
            }}
          >
            Продолжить к обучению
          </Button>
        </div>
      </div>
    </div>
  )
}

