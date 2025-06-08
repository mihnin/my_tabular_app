import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useMainStore = defineStore('main', () => {
  const tableData = ref<any[]>([])
  const selectedFile = ref<File | null>(null)
  const selectedTestFile = ref<File | null>(null) // Новое поле для тестового файла
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const chunkSize = ref(100000)

  // Колонки датасета
  const dateColumn = ref('<нет>')
  const targetColumn = ref('<нет>')
  const idColumn = ref('<нет>')
  const staticFeatures = ref<string[]>([])
  const selectedColumns = ref<string[]>([])
  const considerRussianHolidays = ref(false)
  const fillMethod = ref('mean')
  const groupingColumns = ref<string[]>([])
  const selectedMetric = ref('MAE (Mean absolute error)')
  const selectedModels = ref<string[]>(['*'])
  const selectedPreset = ref('high_quality')
  const timeLimit = ref<number | null>(null)
  const meanOnly = ref(false)
  const trainPredictSave = ref(true)
  const sessionId = ref<string | null>(null)
  const trainingStatus = ref<any>(null)
  const predictionRows = ref<any[]>([])

  // PyCaret models selection
  const selectedPycaretModels = ref<string[]>([])

  // --- DB connection state (обновлено) ---
  const authToken = ref<string | null>(null) // Теперь храним только токен
  const dbConnected = ref(false)
  const dbCheckResult = ref<{ success: boolean; detail: string; access_token?: string } | null>(null)
  const dbTables = ref<string[]>([]) // Новое: для хранения списка таблиц из БД

  // --- Имя таблицы для последней успешной загрузки/сохранения в БД ---
  const uploadDbName = ref<string | null>(null)

  const fileLoaded = ref(false)
  const testFileLoaded = ref(false)
  const problemType = ref('auto') // Новое поле для типа задачи
  const testTableData = ref<any[]>([]) // Новое поле для тестовых данных

  function setTableData(data: any[]) {
    tableData.value = data
  }

  function setChunkSize(size: number) {
    chunkSize.value = size
  }

  function setFile(file: File | null) {
    selectedFile.value = file
    error.value = null
  }

  function setSelectedTestFile(file: File | null) {
    selectedTestFile.value = file
  }

  function setDateColumn(column: string) {
    dateColumn.value = column
  }

  function setTargetColumn(column: string) {
    targetColumn.value = column
  }

  function setIdColumn(column: string) {
    idColumn.value = column
  }

  function setStaticFeatures(features: string[]) {
    staticFeatures.value = features
  }

  function setSelectedColumns(columns: string[]) {
    selectedColumns.value = columns
  }

  function setConsiderRussianHolidays(value: boolean) {
    considerRussianHolidays.value = value
  }

  function setGroupingColumns(columns: string[]) {
    groupingColumns.value = columns
  }

  function setFillMethod(method: string) {
    fillMethod.value = method
  }

  function setSelectedMetric(metric: string) {
    selectedMetric.value = metric
  }

  function setSelectedModels(models: string[]) {
    selectedModels.value = models
  }

  function setSelectedPreset(preset: string) {
    selectedPreset.value = preset
  }

  function setTimeLimit(limit: number | null) {
    timeLimit.value = limit
  }

  function setMeanOnly(value: boolean) {
    meanOnly.value = value
  }

  function setTrainPredictSave(value: boolean) {
    trainPredictSave.value = value
  }

  function setSessionId(id: string | null) {
    sessionId.value = id
  }

  function setTrainingStatus(status: any) {
    trainingStatus.value = status
  }

  function setPredictionRows(rows: any[]) {
    predictionRows.value = rows
  }

  function setSelectedPycaretModels(models: string[]) {
    selectedPycaretModels.value = models
  }

  // Методы для JWT и подключения к БД
  function setAuthToken(token: string | null) {
    authToken.value = token
    // УДАЛЕНО: localStorage.setItem/removeItem
  }

  function setDbConnected(connected: boolean) {
    dbConnected.value = connected
  }

  function setDbCheckResult(result: { success: boolean; detail: string; access_token?: string } | null) {
    dbCheckResult.value = result
  }

  function setDbTables(tables: string[]) {
    dbTables.value = tables
  }

  function setUploadDbName(name: string | null) {
    uploadDbName.value = name
  }

  function setFileLoaded(value: boolean) {
    fileLoaded.value = value
  }
  function setTestFileLoaded(value: boolean) {
    testFileLoaded.value = value
  }
  function setProblemType(type: string) {
    problemType.value = type
  }
  function setTestTableData(data: any[]) {
    testTableData.value = data
  }

  // Метрики для разных типов задач
  const metricsByTask: Record<string, string[]> = {
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
  const metricsDict: Record<string, string> = {
    accuracy: 'Accuracy',
    balanced_accuracy: 'Balanced Accuracy',
    roc_auc: 'ROC AUC',
    f1: 'F1',
    precision: 'Precision',
    recall: 'Recall',
    log_loss: 'LogLoss',
    average_precision: 'AvgPrecision',
    root_mean_squared_error: 'RMSE',
    mean_squared_error: 'MSE',
    mean_absolute_error: 'MAE',
    r2: 'R²',
    pearsonr: 'PearsonR',
    spearmanr: 'SpearmanR'
  }
  const availableMetrics = computed(() => {
    const task = problemType.value || 'auto'
    const allowed = metricsByTask[task] || metricsByTask['auto']
    return allowed.map(key => ({ key, label: metricsDict[key] }))
  })

  return {
    tableData,
    selectedFile,
    selectedTestFile,
    isLoading,
    error,
    chunkSize,
    dateColumn,
    targetColumn,
    idColumn,
    staticFeatures,
    selectedColumns,
    considerRussianHolidays,
    fillMethod,
    groupingColumns,
    selectedMetric,
    selectedModels,
    selectedPreset,
    timeLimit,
    meanOnly,
    trainPredictSave,
    sessionId,
    trainingStatus,
    predictionRows,
    selectedPycaretModels,
    authToken,
    dbConnected,
    dbCheckResult,
    dbTables,
    uploadDbName,
    fileLoaded,
    testFileLoaded,
    problemType,
    testTableData,
    availableMetrics,
    setTableData,
    setChunkSize,
    setFile,
    setSelectedTestFile,
    setDateColumn,
    setTargetColumn,
    setIdColumn,
    setStaticFeatures,
    setSelectedColumns,
    setConsiderRussianHolidays,
    setGroupingColumns,
    setFillMethod,
    setSelectedMetric,
    setSelectedModels,
    setSelectedPreset,
    setTimeLimit,
    setMeanOnly,
    setTrainPredictSave,
    setSessionId,
    setTrainingStatus,
    setPredictionRows,
    setSelectedPycaretModels,
    setAuthToken,
    setDbConnected,
    setDbCheckResult,
    setDbTables,
    setUploadDbName,
    setFileLoaded,
    setTestFileLoaded,
    setProblemType,
    setTestTableData
  }
})