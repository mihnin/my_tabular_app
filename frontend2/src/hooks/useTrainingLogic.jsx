import { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../apiConfig.js';
import { useData } from '../contexts/DataContext';

export function useTrainingLogic({
  uploadedFile,
  trainingConfig,
  updateTrainingStatus,
  sessionId,
  globalTrainingStatus,
  setTotalTrainingTime,
  authToken,
  setAuthToken
}) {
  // --- Auto-save DB state ---
  const { autoSaveEnabled, setAutoSaveEnabled, ensureTablesLoaded } = useData();
  const [dbUsername, setDbUsername] = useState('');
  const [dbPassword, setDbPassword] = useState('');
  const [dbConnecting, setDbConnecting] = useState(false);
  const [dbConnected, setDbConnected] = useState(false);
  const [dbError, setDbError] = useState('');
  const [dbTables, setDbTables] = useState([]);
  const [dbTablesLoading, setDbTablesLoading] = useState(false);
  const [selectedSchema, setSelectedSchema] = useState('');
  const [selectedTable, setSelectedTable] = useState('');
  const [saveTableName, setSaveTableName] = useState('');
  const [autoSaveMenuOpen, setAutoSaveMenuOpen] = useState(false);
  const [saveMode, setSaveMode] = useState('existing');
  const [newTableName, setNewTableName] = useState('');
  const [autoSaveSettings, setAutoSaveSettings] = useState(null);
  const [uploadTableName, setUploadTableName] = useState('');
  const [fileColumns, setFileColumns] = useState([]);
  const { selectedPrimaryKeys, setSelectedPrimaryKeys } = useData();

  // --- Training state ---
  const [trainingStatus, setTrainingStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [currentModel, setCurrentModel] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  const {
    setPredictionRows, predictionProcessed, setPredictionProcessed, trainingStartTime, setTrainingStartTime, setSessionId,
    trainFile, predictFile
  } = useData();
  const pollingRef = useRef(null);
  const tablesLoadedRef = useRef(false);

  // --- Auto-save DB functions ---
  const handleDbConnect = async () => {
    setDbError('');
    setDbConnecting(true);
    setAuthToken(null);
    setDbConnected(false);
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: dbUsername, password: dbPassword })
      });
      if (!response.ok) {
        if (response.status === 401) {
          setDbError('Неверный логин или пароль');
        } else {
          setDbError(`Ошибка сервера: ${response.status}`);
        }
        setDbConnected(false);
        setAuthToken(null);
        setDbConnecting(false);
        return;
      }
      let result = null;
      try {
        result = await response.json();
      } catch (jsonErr) {
        setDbError('Не удалось получить ответ от сервера.');
        setDbConnected(false);
        setDbConnecting(false);
        return;
      }
      if (result.success && result.access_token) {
        setAuthToken(result.access_token);
        setDbConnected(true);
        setDbError('');
        setDbUsername('');
        setDbPassword('');
        // Вместо fetchDbTables используем глобальную функцию
        if (typeof ensureTablesLoaded === 'function') {
          ensureTablesLoaded();
        }
      } else {
        setDbError('Не удалось подключиться к базе данных');
        setDbConnected(false);
      }
    } catch (error) {
      setDbError('Ошибка подключения: ' + error.message);
      setDbConnected(false);
    } finally {
      setDbConnecting(false);
    }
  };

  const handleDbInputChange = (setter) => (e) => {
    setter(e.target.value);
    setDbError('');
  };

  const handleSchemaChange = (schema) => {
    setSelectedSchema(schema);
    setSelectedTable('');
  };

  const handleTableChange = (table) => {
    setSelectedTable(table);
  };

  const handleAutoSaveSetup = async (settings) => {
    try {
      if (!settings) return false;
      // Используем trainFile, полученный из useData выше
      if (settings.mode === 'create') {
        if (!trainFile) {
          setDbError('Файл не выбран. Пожалуйста, загрузите train файл перед созданием таблицы.');
          return false;
        }
        if (!trainFile.name.endsWith('.xlsx') && !trainFile.name.endsWith('.xls')) {
          setDbError('Файл должен быть Excel (.xlsx или .xls)');
          return false;
        }
        const formData = new FormData();
        formData.append('file', trainFile, trainFile.name);
        formData.append('table_name', settings.newTableName);
        formData.append('primary_keys', JSON.stringify(selectedPrimaryKeys));
        formData.append('create_table_only', 'true');
        formData.append('db_schema', settings.selectedSchema);
        // --- DEBUG: log all FormData values before sending ---
        console.log('Sending /create-table-from-file:', {
          file: trainFile,
          fileName: trainFile?.name,
          table_name: settings.newTableName,
          primary_keys: selectedPrimaryKeys,
          create_table_only: 'true',
          db_schema: settings.selectedSchema,
          authToken,
        });
        if (formData && formData.entries) {
          for (const [key, value] of formData.entries()) {
            console.log('FormData:', key, value);
          }
        }
        const response = await fetch(`${API_BASE_URL}/create-table-from-file`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`
          },
          body: formData
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
          setDbError(result.detail || 'Ошибка создания таблицы');
          return false;
        }
        setUploadTableName(settings.newTableName);
        setAutoSaveSettings({
          mode: settings.mode,
          selectedSchema: settings.selectedSchema,
          selectedTable: '',
          newTableName: settings.newTableName,
          primaryKeys: selectedPrimaryKeys
        });
        setAutoSaveEnabled(true);
        return true;
      } else {
        if (!trainFile) {
          setDbError('Файл не выбран. Пожалуйста, загрузите train файл перед проверкой структуры таблицы.');
          return false;
        }
        if (!trainFile.name.endsWith('.xlsx') && !trainFile.name.endsWith('.xls')) {
          setDbError('Файл должен быть Excel (.xlsx или .xls)');
          return false;
        }
        const [schema, ...tableParts] = settings.selectedTable.split('.');
        const tableName = tableParts.join('.');
        const formData = new FormData();
        formData.append('file', trainFile, trainFile.name);
        formData.append('table_name', tableName);
        formData.append('db_schema', schema);
        const response = await fetch(`${API_BASE_URL}/check-df-matches-table-schema`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`
          },
          body: formData
        });
        const result = await response.json();
        if (result.success) {
          setAutoSaveSettings({
            mode: settings.mode,
            selectedSchema: settings.selectedSchema,
            selectedTable: settings.selectedTable,
            newTableName: settings.newTableName || '',
          });
          setAutoSaveEnabled(true);
        } else {
          setDbError(result.detail || 'Ошибка проверки структуры');
          return false;
        }
      }
      setDbError('');
      return true;
    } catch (error) {
      setDbError(error.message || 'Ошибка настройки автосохранения');
      return false;
    }
  };

  // Подключение к БД при наличии токена
  useEffect(() => {
    if (
      authToken &&
      !dbTablesLoading &&
      dbTables.length === 0
    ) {
      ensureTablesLoaded();
    } else if (!authToken) {
      tablesLoadedRef.current = false;
    }
    // eslint-disable-next-line
  }, [authToken, dbTablesLoading, dbTables.length, ensureTablesLoaded]);

  // --- Training logic ---
  const resetTrainingState = () => {
    setTrainingStatus(null);
    setSessionId(null);
    setTotalTrainingTime('');
    setTrainingStartTime(null);
  };

  const getTrainingStatus = () => {
    if (globalTrainingStatus) {
      if (['completed', 'complete'].includes(globalTrainingStatus.status)) {
        return 'completed';
      }
      if (globalTrainingStatus.status === 'failed') {
        return 'error';
      }
      if (['initializing', 'running'].includes(globalTrainingStatus.status)) {
        return 'running';
      }
    }
    return trainingStatus;
  };

  const getStatusMessage = () => {
    if (!globalTrainingStatus) return '';
    const status = globalTrainingStatus.status;
    if (status === 'initializing') return 'Инициализация обучения...';
    if (status === 'running') return `Обучение в процессе (${globalTrainingStatus.progress ?? 0}%)`;
    if (status === 'completed') return 'Обучение успешно завершено!';
    if (status === 'failed') return 'Ошибка при обучении';
    return status;
  };

  const getCurrentProgress = () => {
    return globalTrainingStatus?.progress ?? progress;
  };

  const getCurrentModel = () => {
    return globalTrainingStatus?.current_model || currentModel;
  };

  const getBestModel = () => {
    if (globalTrainingStatus?.best_model) return globalTrainingStatus.best_model;
    // Попробуем вычислить из leaderboard
    const lb = globalTrainingStatus?.leaderboard;
    if (Array.isArray(lb) && lb.length > 0) {
      // Сначала ищем колонку rank
      const ranked = lb.find(r => Number(r.rank) === 1);
      if (ranked?.model) return ranked.model;
      // Если rank нет — берем первую строку
      return lb[0].model || '';
    }
    return '';
  };

  const getBestModelMetric = () => {
    if (globalTrainingStatus?.best_model_metric) return globalTrainingStatus.best_model_metric;
    const lb = globalTrainingStatus?.leaderboard;
    if (Array.isArray(lb) && lb.length > 0) {
      const metricKey = (globalTrainingStatus?.training_params?.evaluation_metric) || 'score_val';
      const hasMetric = metricKey && lb[0]?.hasOwnProperty(metricKey);
      const ranked = lb.find(r => Number(r.rank) === 1) || lb[0];
      if (hasMetric) {
        return ranked[metricKey];
      }
    }
    return '';
  };

  const getAverageMetric = () => {
    if (globalTrainingStatus?.average_metric) return globalTrainingStatus.average_metric;
    const lb = globalTrainingStatus?.leaderboard;
    if (Array.isArray(lb) && lb.length > 0) {
      const metricKey = (globalTrainingStatus?.training_params?.evaluation_metric) || 'score_val';
      if (metricKey && lb[0]?.hasOwnProperty(metricKey)) {
        const vals = lb.map(r => Number(r[metricKey])).filter(v => !isNaN(v));
        if (vals.length > 0) {
          const avg = vals.reduce((a,b)=>a+b,0)/vals.length;
          return avg.toFixed(4);
        }
      }
    }
    return '';
  };

  const getTotalTrainingTime = () => {
    return globalTrainingStatus?.total_training_time || '';
  };

  // Очистка polling при размонтировании
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);

  // Опрос статуса при получении sessionId
  useEffect(() => {
    if (sessionId && getTrainingStatus() === 'running') {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
      pollingRef.current = setInterval(pollTrainingStatus, 2000);
      pollTrainingStatus();
    } else if (getTrainingStatus() === 'completed' || getTrainingStatus() === 'error') {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      // Do not reset sessionId or trainingStatus here
    }
    // eslint-disable-next-line
  }, [sessionId, getTrainingStatus()]);

  // useEffect for globalTrainingStatus?.status больше не нужен для polling

  // Таймер elapsedTime
  useEffect(() => {
    let timeInterval = null;
    if (trainingStatus === 'running' && trainingStartTime) {
      timeInterval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - trainingStartTime) / 1000));
      }, 1000);
    } else {
      setElapsedTime(0);
    }
    return () => {
      if (timeInterval) clearInterval(timeInterval);
    };
  }, [trainingStatus, trainingStartTime]);

  // --- Retry download helper ---
  const downloadPredictionWithRetry = async (sessionId, retries = 5, delay = 1500) => {
    for (let i = 0; i < retries; i++) {
      try {
        const fileResp = await fetch(`${API_BASE_URL}/download_prediction/${sessionId}`);
        if (fileResp.ok) {
          return await fileResp.blob();
        }
        if (fileResp.status === 404 && i < retries - 1) {
          await new Promise(res => setTimeout(res, delay));
          continue;
        }
        throw new Error('Ошибка скачивания прогноза');
      } catch (e) {
        if (i === retries - 1) throw e;
        await new Promise(res => setTimeout(res, delay));
      }
    }
    throw new Error('Файл не найден после нескольких попыток');
  };

  // Опрос статуса обучения
  const pollTrainingStatus = async () => {
    if (!sessionId) return;
    const currentStatus = getTrainingStatus();
    if (currentStatus === 'completed' || currentStatus === 'error') {
      return;
    }
    try {
      const statusResp = await fetch(`${API_BASE_URL}/training_status/${sessionId}`);
      if (!statusResp.ok) throw new Error('Failed to fetch training status');
      const status = await statusResp.json();
      updateTrainingStatus(status);
      if (status.current_model) setCurrentModel(status.current_model);
      if (typeof status.progress === 'number') setProgress(status.progress);
      if (["completed", "complete", "failed"].includes(status.status)) {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        if (["completed", "complete"].includes(status.status)) {
          try {
            const blob = await downloadPredictionWithRetry(sessionId);
            const arrayBuffer = await blob.arrayBuffer();
            const XLSX = await import('xlsx');
            const workbook = XLSX.read(arrayBuffer, { type: 'array' });
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
            const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });
            if (rows.length > 1) {
              const headers = rows[0];
              // Фильтруем технические колонки 0.1-0.9
              const filteredHeaders = headers.filter(h => !/^0\.[1-9]$/.test(h));
              const dataRows = rows.slice(1);
              const parsedRows = dataRows.map(row =>
                Object.fromEntries(filteredHeaders.map((h, i) => [h, row[headers.indexOf(h)]]))
              );
              setPredictionRows(parsedRows);
            }
            if (trainingStartTime) {
              const endTime = Date.now();
              const diffMs = endTime - trainingStartTime;
              const minutes = Math.floor(diffMs / 60000);
              const seconds = Math.floor((diffMs % 60000) / 1000);
              const finalTime = `${minutes}m ${seconds}s`;
              setTotalTrainingTime(finalTime);
              setTrainingStartTime(null); // Сбросить только после завершения обучения
              setPredictionProcessed(true);
            }
          } catch (e) {
            alert('Ошибка при обработке прогноза: ' + (e instanceof Error ? e.message : e));
          }
        }
        // Do not reset sessionId or trainingStatus here
      }
    } catch (error) {
      // Можно добавить обработку ошибок
    }
  };

  const handleStartTraining = async () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setPredictionRows([]);
    setPredictionProcessed(false);
    setElapsedTime(0); // Сбросить таймер
    setTotalTrainingTime(''); // Сбросить итоговое время
    // --- Проверка наличия trainFile, predictFile и целевой колонки ---
    if (!trainFile || !predictFile) {
      alert('Ошибка: Загрузите оба файла (train и predict) перед запуском обучения.');
      return;
    }
    if (!trainingConfig || !trainingConfig.targetColumn || trainingConfig.targetColumn === 'none') {
      alert('Ошибка: Выберите целевую колонку перед запуском обучения.');
      return;
    }
    setTrainingStatus('running');
    setProgress(0);
    setCurrentModel('Инициализация...');
    setTotalTrainingTime('');
    setTrainingStartTime(Date.now()); // Стартуем отсчёт времени
    updateTrainingStatus({ status: 'initializing', progress: 0 });
    try {
      const params = {
        target_column: trainingConfig.targetColumn,
        problem_type: trainingConfig.problemType,
        evaluation_metric: trainingConfig.selectedMetric,
        autogluon_preset: trainingConfig.autogluonPreset,
        models_to_train: trainingConfig.selectedAutogluonModels?.includes('*') ? '*' : (trainingConfig.selectedAutogluonModels?.length > 0 ? trainingConfig.selectedAutogluonModels : '*'),
        fill_missing_method: trainingConfig.missingValueMethod,
        training_time_limit: trainingConfig.trainingTimeLimit,
      };
      // --- Add DB save params if enabled ---
      if (autoSaveEnabled && autoSaveSettings && autoSaveSettings.selectedSchema) {
        params.upload_table_schema = autoSaveSettings.selectedSchema;
        if (autoSaveSettings.mode === 'existing' && autoSaveSettings.selectedTable) {
          params.upload_table_name = autoSaveSettings.selectedTable.split('.').pop();
        }
        if (autoSaveSettings.mode === 'create' && autoSaveSettings.newTableName) {
          params.upload_table_name = autoSaveSettings.newTableName;
        }
      }
      const formData = new FormData();
      formData.append('params', JSON.stringify(params));
      formData.append('train_file', trainFile, trainFile.name);
      if (predictFile) {
        formData.append('test_file', predictFile, predictFile.name);
      }
      // --- Endpoint selection ---
      const endpoint = `${API_BASE_URL}/train_prediction_save/`;
      const headers = { 'Accept': 'application/json' };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        headers
      });
      if (!response.ok) {
        setTrainingStatus('error');
        setDbError('Ошибка запуска обучения');
        return;
      }
      const result = await response.json();
      if ((result.success === true || result.status === 'accepted') && result.session_id) {
        setSessionId(result.session_id);
        setTrainingStatus('running');
        setDbError('');
        // --- Запускаем опрос статуса только после успешного ответа ---
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
        }
        pollingRef.current = setInterval(pollTrainingStatus, 2000);
        pollTrainingStatus();
      } else {
        setTrainingStatus('error');
        setDbError(result.detail || result.message || 'Неизвестная ошибка при запуске обучения');
      }
    } catch (error) {
      setTrainingStatus('error');
      setDbError('Ошибка запуска обучения: ' + error.message);
    }
  };

  // --- Populate fileColumns from trainFile ---
  useEffect(() => {
    async function extractColumnsFromTrainFile(file) {
      if (!file) {
        setFileColumns([]);
        setSelectedPrimaryKeys([]);
        return;
      }
      try {
        // Only handle Excel files (.xlsx, .xls)
        if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
          const arrayBuffer = await file.arrayBuffer();
          const XLSX = await import('xlsx');
          const workbook = XLSX.read(arrayBuffer, { type: 'array' });
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });
          if (rows.length > 0) {
            const headers = rows[0];
            // Фильтруем технические колонки 0.1-0.9
            const filteredHeaders = headers.filter(h => !/^0\.[1-9]$/.test(h));
            setFileColumns(filteredHeaders);
            setSelectedPrimaryKeys([]);
          } else {
            setFileColumns([]);
            setSelectedPrimaryKeys([]);
          }
        } else if (file.name.endsWith('.csv')) {
          // CSV: read first line for headers
          const text = await file.text();
          const firstLine = text.split(/\r?\n/)[0];
          const headers = firstLine.split(',').map(h => h.trim());
          const filteredHeaders = headers.filter(h => !/^0\.[1-9]$/.test(h));
          setFileColumns(filteredHeaders);
          setSelectedPrimaryKeys([]);
        } else {
          setFileColumns([]);
          setSelectedPrimaryKeys([]);
        }
      } catch (e) {
        setFileColumns([]);
        setSelectedPrimaryKeys([]);
      }
    }
    extractColumnsFromTrainFile(trainFile);
  }, [trainFile, setSelectedPrimaryKeys]);

  // Сброс selectedPrimaryKeys при отключении от БД
  useEffect(() => {
    if (!dbConnected) {
      setSelectedPrimaryKeys([]);
    }
  }, [dbConnected, setSelectedPrimaryKeys]);

  return {
    // --- Auto-save DB state ---
    dbUsername,
    dbPassword,
    dbConnecting,
    dbConnected,
    dbError,
    dbTables,
    dbTablesLoading,
    selectedSchema,
    setSelectedSchema, // <-- добавлено для передачи в компоненты
    selectedTable,
    setSelectedTable, // <-- добавлено для передачи в компоненты
    saveTableName,
    autoSaveMenuOpen,
    saveMode,
    setSaveMode, // <-- добавлено для передачи в компоненты
    newTableName,
    setNewTableName,
    autoSaveSettings,
    setAutoSaveSettings,
    uploadTableName,
    fileColumns,
    selectedPrimaryKeys,
    setAutoSaveEnabled,
    handleDbConnect,
    handleDbInputChange,
    handleSchemaChange,
    handleTableChange,
    handleAutoSaveSetup,
    // --- Training state ---
    trainingStatus,
    progress,
    currentModel,
    elapsedTime,
    // --- Methods ---
    resetTrainingState,
    getTrainingStatus,
    getStatusMessage,
    getCurrentProgress,
    getCurrentModel,
    handleStartTraining,
    // Метрики для Training.jsx
    getBestModel,
    getBestModelMetric,
    getAverageMetric,
    getTotalTrainingTime,
  };
}