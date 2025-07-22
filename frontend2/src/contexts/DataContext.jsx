import React, { createContext, useContext, useState, useCallback, useRef } from 'react'
import { API_BASE_URL } from '../apiConfig.js'

const DataContext = createContext()

export function DataProvider({ children }) {
  // --- OLD STATE ---
  const [uploadedData, setUploadedData] = useState(null)
  const [dataSource, setDataSource] = useState(null) // 'file' or 'database'
  const [selectedTable, setSelectedTable] = useState(null)
  // --- TRAIN/TEST TABULAR STATE ---
  const [trainData, setTrainData] = useState(null)
  const [trainFile, setTrainFile] = useState(null)
  const [trainSource, setTrainSource] = useState(null) // 'file' or 'database'
  const [trainActiveTab, setTrainActiveTab] = useState('file')
  const [trainPreviewData, setTrainPreviewData] = useState(null)
  const [trainSelectedDbTable, setTrainSelectedDbTable] = useState('')
  const [trainSelectedSchema, setTrainSelectedSchema] = useState('')
  const [trainTablePreview, setTrainTablePreview] = useState(null)
  const [predictData, setPredictData] = useState(null)
  const [predictFile, setPredictFile] = useState(null)
  const [predictSource, setPredictSource] = useState(null)
  const [predictActiveTab, setPredictActiveTab] = useState('file')
  const [predictPreviewData, setPredictPreviewData] = useState(null)
  const [predictSelectedDbTable, setPredictSelectedDbTable] = useState('')
  const [predictSelectedSchema, setPredictSelectedSchema] = useState('')
  const [predictTablePreview, setPredictTablePreview] = useState(null)

  // Training-related state
  const [uploadedFile, setUploadedFile] = useState(null)
  const [trainingConfig, setTrainingConfig] = useState(null)
  const [trainingStatus, setTrainingStatus] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [authToken, setAuthToken] = useState(null)
  const [trainPredictSave, setTrainPredictSave] = useState(false)
  const [predictionRows, setPredictionRows] = useState([])
  const [dbConnected, setDbConnected] = useState(false)
  const [dbUsername, setDbUsername] = useState("")
  const [dbPassword, setDbPassword] = useState("")
  const [uploadDbName, setUploadDbName] = useState('')
  const [totalTrainingTime, setTotalTrainingTime] = useState('')
  const [predictionProcessed, setPredictionProcessed] = useState(false);
  const [previewData, setPreviewData] = useState(null)
  const [tablePreview, setTablePreview] = useState(null)
  const [activeTab, setActiveTab] = useState('file')
  const [dbTables, setDbTables] = useState([])
  const [dbTablesLoading, setDbTablesLoading] = useState(false)
  const [dbError, setDbError] = useState('')
  const [trainingStartTime, setTrainingStartTime] = useState(null);
  // --- AUTOSAVE GLOBAL STATE ---
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(false);
  // --- PRIMARY KEYS GLOBAL STATE ---
  const [selectedPrimaryKeys, setSelectedPrimaryKeys] = useState([]);
  // --- ANALYSIS CACHE (for tabular analysis) ---
  const [analysisCache, setAnalysisCache] = useState({});

  const tablesLoadedRef = useRef(false);

  // Логирование всех изменений состояния
  // React.useEffect(() => {
  //   console.log('[DataContext] dbConnected changed:', dbConnected);
  // }, [dbConnected]);
  // React.useEffect(() => {
  //   console.log('[DataContext] dbTables changed:', dbTables);
  // }, [dbTables]);
  // React.useEffect(() => {
  //   console.log('[DataContext] dbTablesLoading changed:', dbTablesLoading);
  // }, [dbTablesLoading]);
  // React.useEffect(() => {
  //   console.log('[DataContext] dbError changed:', dbError);
  // }, [dbError]);
  // React.useEffect(() => {
  //   console.log('[DataContext] authToken changed:', authToken);
  // }, [authToken]);
  // React.useEffect(() => {
  //   console.log('[DataContext] selectedPrimaryKeys changed:', selectedPrimaryKeys);
  // }, [selectedPrimaryKeys]);
  // React.useEffect(() => {
  //   console.log('[DataContext] trainingStatus changed:', trainingStatus);
  // }, [trainingStatus]);
  // React.useEffect(() => {
  //   console.log('[DataContext] trainingConfig changed:', trainingConfig);
  // }, [trainingConfig]);
  // React.useEffect(() => {
  //   console.log('[DataContext] sessionId changed:', sessionId);
  // }, [sessionId]);
  // React.useEffect(() => {
  //   console.log('[DataContext] predictionRows changed:', predictionRows);
  // }, [predictionRows]);
  // React.useEffect(() => {
  //   console.log('[DataContext] autoSaveEnabled changed:', autoSaveEnabled);
  // }, [autoSaveEnabled]);

  /* -------------------- DB helpers -------------------- */
  const clearDbState = useCallback(() => {
    // console.log('[DataContext] clearDbState called');
    setAuthToken(null);
    setDbConnected(false);
    setDbTables([]);
    setDbSchemas && setDbSchemas([]);
    setDbTablesBySchema && setDbTablesBySchema({});
    setDbError('');
  }, []);

  const ensureTablesLoaded = useCallback(async () => {
    if (!authToken || !dbConnected || dbTablesLoading || dbTables.length > 0 || tablesLoadedRef.current) {
      return;
    }
    tablesLoadedRef.current = true;
    setDbTablesLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/get-tables`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        }
      });
      const result = await response.json();
      if (result.success) {
        setDbTables(Object.keys(result.tables).map(schema => ({ schema, tables: result.tables[schema] })));
      }
    } catch (e) {
      setDbError('Ошибка загрузки таблиц: ' + (e.message || e));
    } finally {
      setDbTablesLoading(false);
    }
  }, [authToken, dbConnected, dbTablesLoading, dbTables.length]);

  const refreshTables = useCallback(async () => {
    if (!authToken || !dbConnected) return;
    setDbTablesLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/get-tables`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        }
      });
      const result = await response.json();
      if (result.success) {
        setDbTables(Object.keys(result.tables).map(schema => ({ schema, tables: result.tables[schema] })));
      } else {
        setDbError('Ошибка загрузки таблиц: ' + (result.message || 'Неизвестная ошибка'));
      }
    } catch (e) {
      setDbError('Ошибка загрузки таблиц: ' + (e.message || e));
    } finally {
      setDbTablesLoading(false);
    }
  }, [authToken, dbConnected]);

  // --- NEW METHODS FOR TABULAR ---
  const updateTrainData = (data, source, fileOrTable = null) => {
    setTrainData(data)
    setTrainSource(source)
    setTrainFile(source === 'file' ? fileOrTable : null)
  }
  const updatePredictData = (data, source, fileOrTable = null) => {
    setPredictData(data)
    setPredictSource(source)
    setPredictFile(source === 'file' ? fileOrTable : null)
  }
  const clearTrainData = () => {
    setTrainData(null)
    setTrainSource(null)
    setTrainFile(null)
  }
  const clearPredictData = () => {
    setPredictData(null)
    setPredictSource(null)
    setPredictFile(null)
  }

  const updateData = (data, source, table = null) => {
    setUploadedData(data)
    setDataSource(source)
    setSelectedTable(table)
  }

  const clearData = () => {
    setUploadedData(null)
    setDataSource(null)
    setSelectedTable(null)
  }

  const updateTrainingConfig = (config) => {
    setTrainingConfig(config)
  }

  const updateTrainingStatus = (status) => {
    setTrainingStatus(status)
  }

  const resetTrainingState = () => {
    setTrainingStatus(null)
    setSessionId(null)
    setTotalTrainingTime('')
    setPredictionRows([])
    setPredictionProcessed(false)
  }

  return (
    <DataContext.Provider value={{
      // Data state
      uploadedData,
      dataSource,
      selectedTable,
      updateData,
      clearData,
      // Tabular train/predict
      trainData,
      setTrainData,
      trainFile,
      setTrainFile,
      trainSource,
      setTrainSource,
      predictData,
      setPredictData,
      predictFile,
      setPredictFile,
      predictSource,
      setPredictSource,
      updateTrainData,
      updatePredictData,
      clearTrainData,
      clearPredictData,
      // Training state
      uploadedFile,
      setUploadedFile,
      trainingConfig,
      updateTrainingConfig,
      trainingStatus,
      updateTrainingStatus,
      resetTrainingState,
      sessionId,
      setSessionId,
      authToken,
      setAuthToken,
      trainPredictSave,
      setTrainPredictSave,
      predictionRows,
      setPredictionRows,
      dbConnected,
      setDbConnected,
      dbUsername,
      setDbUsername,
      dbPassword,
      setDbPassword,
      uploadDbName,
      setUploadDbName,
      totalTrainingTime,
      setTotalTrainingTime,
      predictionProcessed,
      setPredictionProcessed,
      previewData,
      setPreviewData,
      tablePreview,
      setTablePreview,
      activeTab,
      setActiveTab,
      dbTables,
      setDbTables,
      dbTablesLoading,
      setDbTablesLoading,
      dbError,
      setDbError,
      trainingStartTime,
      setTrainingStartTime,
      // AUTOSAVE GLOBAL STATE
      autoSaveEnabled,
      setAutoSaveEnabled,
      // Active tab and preview data for train/predict
      trainActiveTab,
      setTrainActiveTab,
      trainPreviewData,
      setTrainPreviewData,
      trainSelectedDbTable,
      setTrainSelectedDbTable,
      trainSelectedSchema,
      setTrainSelectedSchema,
      trainTablePreview,
      setTrainTablePreview,
      predictActiveTab,
      setPredictActiveTab,
      predictPreviewData,
      setPredictPreviewData,
      predictSelectedDbTable,
      setPredictSelectedDbTable,
      predictSelectedSchema,
      setPredictSelectedSchema,
      predictTablePreview,
      setPredictTablePreview,
      selectedPrimaryKeys,
      setSelectedPrimaryKeys,
      clearDbState,
      ensureTablesLoaded,
      refreshTables,
      analysisCache,
      setAnalysisCache
    }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const context = useContext(DataContext)
  if (!context) {
    throw new Error('useData must be used within a DataProvider')
  }
  return context
}
