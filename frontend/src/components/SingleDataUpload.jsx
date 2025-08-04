import React, { useState, useRef, useEffect } from 'react';
import { parseFile, validateFileSize, validateFileType, formatFileSize } from '../utils/fileParser';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx';
import { Button } from '@/components/ui/button.jsx';
import { Input } from '@/components/ui/input.jsx';
import { Label } from '@/components/ui/label.jsx';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx';
import { Upload, Database, FileText, CheckCircle, AlertCircle, Eye, ChevronDown, ChevronUp } from 'lucide-react';
import { API_BASE_URL } from '../apiConfig.js';
import { useData } from '../contexts/DataContext';

export default function SingleDataUpload({
  title = '',
  description = '',
  uploadedFile,
  setUploadedFile,
  previewData,
  setPreviewData,
  activeTab,
  setActiveTab,
  dbConnected,
  setDbConnected,
  dbTables,
  setDbTables,
  dbTablesLoading,
  setDbTablesLoading,
  dbError,
  setDbError,
  authToken,
  setAuthToken,
  selectedDbTable,
  setSelectedDbTable,
  selectedSchema,
  setSelectedSchema,
  tablePreview,
  setTablePreview,
  updateData,
  mode = 'train', // 'train' или 'predict'
  ...rest
}) {
  // --- File upload state ---
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const previewRef = useRef(null);
  const fileInputRef = useRef(null);

  // --- DB connection/auth state ---
  const [localUsername, setLocalUsername] = useState('');
  const [localPassword, setLocalPassword] = useState('');
  const [dbConnecting, setDbConnecting] = useState(false);
  const [dbSuccess, setDbSuccess] = useState(false);

  // --- Table preview state ---
  const [tablePreviewLoading, setTablePreviewLoading] = useState(false);
  const [tablePreviewError, setTablePreviewError] = useState('');
  const [previewVisible, setPreviewVisible] = useState(false);
  const [tableLoadingFromDb, setTableLoadingFromDb] = useState(false);
  // --- Success notification and UI lock ---
  const [dbSuccessLoaded, setDbSuccessLoaded] = useState(false);
  // Toggle for credentials visibility in DB tab
  const [credOpen, setCredOpen] = useState(!dbConnected);

  const {
    setTrainFile,
    setTrainPreviewData,
    setTrainData,
    setPredictFile,
    setPredictPreviewData,
    setPredictData,
    ensureTablesLoaded
  } = useData();

  // Collapse/expand when connection status changes
  useEffect(()=>{
    setCredOpen(!dbConnected);
  },[dbConnected]);

  // --- File upload logic ---
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setFileError('');
    setShowSuccess(false); // Сбросить сразу при старте
    setUploadedFile(null); // Сбросить файл перед загрузкой
    setPreviewData(null); // Сбросить предпросмотр перед загрузкой
    setTablePreview && setTablePreview(null);
    setTablePreviewError && setTablePreviewError('');
    setSelectedDbTable && setSelectedDbTable('');
    try {
      if (!validateFileSize(file, 100)) {
        setFileError('Размер файла превышает 100 МБ');
        return;
      }
      if (!validateFileType(file)) {
        setFileError('Поддерживаются только файлы форматов CSV, XLSX, XLS');
        return;
      }
      setFileLoading(true);
      setUploadedFile(file);
      const parsedData = await parseFile(file);
      const previewRows = parsedData.rows.slice(0, 5);
      setPreviewData({
        columns: parsedData.columns,
        rows: previewRows,
        totalRows: parsedData.totalRows, // <-- используем именно totalRows с сервера
        fullData: parsedData
      });
      setShowSuccess(true); // Показываем сообщение сразу после успешного парсинга
      updateData && updateData(parsedData, 'file', file);
    } catch (error) {
      setFileError(error.message || 'Произошла ошибка при обработке файла');
      setUploadedFile(null);
      setPreviewData(null);
      setShowSuccess(false);
    } finally {
      setFileLoading(false);
    }
  };

  const handleClearFile = () => {
    setUploadedFile(null);
    setPreviewData(null);
    setFileError('');
    setFileLoading(false);
    setTablePreview && setTablePreview(null);
    setTablePreviewError && setTablePreviewError('');
    setSelectedDbTable && setSelectedDbTable('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Drag & Drop
  const handleDragEnter = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true); };
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(false); };
  const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); };
  const handleDrop = (e) => {
    e.preventDefault(); e.stopPropagation(); setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload({ target: { files: [files[0]] } });
  };

  // DB connect logic
  const handleDbConnect = async () => {
    setDbError && setDbError('');
    setDbSuccess(false);
    setDbConnecting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: localUsername, password: localPassword })
      });
      if (!response.ok) {
        setDbError && setDbError('Ошибка подключения');
        setDbConnected && setDbConnected(false);
        setAuthToken && setAuthToken(null);
        setDbConnecting(false);
        return;
      }
      const result = await response.json();
      if (result.success && result.access_token) {
        setAuthToken && setAuthToken(result.access_token);
        setDbConnected && setDbConnected(true);
        setDbSuccess(true);
        setDbError && setDbError('');
        setLocalUsername('');
        setLocalPassword('');
        setTimeout(() => setDbSuccess(false), 1800);
        setCredOpen(false);
        // После успешного логина: больше не вызываем ensureTablesLoaded здесь
      } else {
        setDbError && setDbError('Не удалось подключиться к базе данных');
        setDbConnected && setDbConnected(false);
        setAuthToken && setAuthToken(null);
      }
    } catch (e) {
      setDbError && setDbError(`Ошибка сети: ${e.message}`);
      setDbConnected && setDbConnected(false);
      setAuthToken && setAuthToken(null);
    } finally {
      setDbConnecting(false);
    }
  };

  // DB disconnect
  const handleDbDisconnect = () => {
    setAuthToken && setAuthToken(null);
    setDbConnected && setDbConnected(false);
    setDbSuccess(false);
    setDbError && setDbError('');
    setLocalUsername('');
    setLocalPassword('');
    setDbTables && setDbTables([]);
    setSelectedDbTable && setSelectedDbTable('');
    setSelectedSchema && setSelectedSchema('');
    setTablePreview && setTablePreview(null);
    setTablePreviewError && setTablePreviewError('');
    setTableLoadingFromDb(false);
    setPreviewData && setPreviewData(null);
    setUploadedFile && setUploadedFile(null);
    setCredOpen(true);
  };

  // Получение схем и таблиц
  const tablesLoadedRef = useRef(false);
  useEffect(() => {
    // Только если таблицы еще не загружены и не идет загрузка
    if (
      authToken &&
      !dbTablesLoading &&
      dbTables.length === 0
    ) {
      ensureTablesLoaded();
    } else if (!authToken) {
      setDbConnected && setDbConnected(false);
      tablesLoadedRef.current = false;
    }
  }, [authToken, dbTablesLoading, dbTables.length, ensureTablesLoaded]);

  // Fetch table preview
  const fetchTablePreview = async (tableName) => {
    setTablePreviewLoading(true);
    setTablePreview && setTablePreview(null);
    setTablePreviewError && setTablePreviewError('');
    try {
      const schema = selectedSchema;
      const table = tableName;
      if (!schema || !table) {
        setTablePreviewError && setTablePreviewError('Некорректное имя таблицы');
        setTablePreviewLoading(false);
        return;
      }
      const url = `${API_BASE_URL}/get-table-preview`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ db_schema: schema, table }) // <-- исправлено поле
      });
      const result = await response.json();
      if (result.success && Array.isArray(result.data) && result.data.length > 0) {
        const columns = Object.keys(result.data[0]);
        const rows = result.data.map(rowObj => columns.map(col => rowObj[col]));
        setTablePreview && setTablePreview({ columns, rows });
      } else if (result.success && Array.isArray(result.data) && result.data.length === 0) {
        setTablePreview && setTablePreview({ columns: [], rows: [] });
        setTablePreviewError && setTablePreviewError('Таблица пуста');
      } else {
        setTablePreviewError && setTablePreviewError('Не удалось получить предпросмотр таблицы');
      }
    } catch (e) {
      setTablePreviewError && setTablePreviewError('Ошибка при получении предпросмотра таблицы');
    } finally {
      setTablePreviewLoading(false);
    }
  };

  // Effect: fetch preview when table selected
  useEffect(() => {
    if (selectedDbTable && authToken) {
      fetchTablePreview(selectedDbTable);
    } else {
      setTablePreview && setTablePreview(null);
      setTablePreviewError && setTablePreviewError('');
    }
    // eslint-disable-next-line
  }, [selectedDbTable, authToken]);

  // Effect: show animation when tablePreview appears
  useEffect(() => {
    if (tablePreview && tablePreview.columns && tablePreview.rows && tablePreview.rows.length > 0 && !tablePreviewLoading && !tablePreviewError) {
      setPreviewVisible(false);
      requestAnimationFrame(() => setPreviewVisible(true));
    } else {
      setPreviewVisible(false);
    }
  }, [tablePreview, tablePreviewLoading, tablePreviewError]);

  // Load table from DB
  const loadTableFromDb = async () => {
    if (!selectedDbTable || !authToken) return;
    setTablePreviewError && setTablePreviewError('');
    setTableLoadingFromDb(true);
    try {
      const schema = selectedSchema;
      const table = selectedDbTable;
      if (!schema || !table) {
        setTablePreviewError && setTablePreviewError('Некорректное имя таблицы');
        return;
      }
      const response = await fetch(`${API_BASE_URL}/download-table-from-db`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ db_schema: schema, table })
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        setTablePreviewError && setTablePreviewError(err.detail || 'Ошибка загрузки таблицы из БД');
        return;
      }
      const blob = await response.blob();
      const file = new File([blob], `${table}.xlsx`, { type: blob.type });
      const parsedData = await parseFile(file);
      const previewRows = parsedData.rows.slice(0, 10);
      if (mode === 'train') {
        setTrainFile(file);
        setTrainPreviewData({
          columns: parsedData.columns,
          rows: previewRows,
          totalRows: parsedData.totalRows, // <-- исправлено: используем totalRows с бэкенда
          fullData: parsedData
        });
        setTrainData(parsedData);
      } else if (mode === 'predict') {
        setPredictFile(file);
        setPredictPreviewData({
          columns: parsedData.columns,
          rows: previewRows,
          totalRows: parsedData.totalRows, // <-- исправлено: используем totalRows с бэкенда
          fullData: parsedData
        });
        setPredictData(parsedData);
      }
      setDbSuccessLoaded(true);
    } catch (error) {
      setTablePreviewError && setTablePreviewError('Ошибка загрузки данных из БД: ' + (error?.message || error));
      if (mode === 'train') {
        setTrainFile(null);
        setTrainPreviewData(null);
        setTrainData(null);
      } else if (mode === 'predict') {
        setPredictFile(null);
        setPredictPreviewData(null);
        setPredictData(null);
      }
    } finally {
      setTableLoadingFromDb(false);
    }
  };

  // --- Автоматический скролл к предпросмотру ---
  useEffect(() => {
    if (previewData && previewRef.current) {
      setTimeout(() => {
        previewRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [previewData]);

  // --- UI ---
  return (
    <div className="mb-10">
      <h2 className="text-xl font-bold mb-2">{title}</h2>
      {description && <p className="text-muted-foreground mb-4">{description}</p>}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="file" className="flex items-center space-x-2">
            <FileText size={16} />
            <span>Загрузка из файла</span>
          </TabsTrigger>
          <TabsTrigger value="database" className="flex items-center space-x-2">
            <Database size={16} />
            <span>Загрузка из БД</span>
          </TabsTrigger>
        </TabsList>
        <TabsContent value="file" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Upload className="text-primary" size={20} />
                <span>Загрузка файла</span>
              </CardTitle>
              <CardDescription>Поддерживаются форматы: CSV, Excel (.xlsx, .xls)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div 
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragOver ? 'border-primary bg-primary/5' : 'border-border'}`}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <Upload className={`mx-auto mb-4 ${isDragOver ? 'text-primary' : 'text-muted-foreground'}`} size={48} />
                <div className="space-y-2">
                  <p className="text-lg font-medium">
                    {isDragOver ? 'Отпустите файл для загрузки' : 'Перетащите файл сюда или выберите файл'}
                  </p>
                  <p className="text-sm text-muted-foreground">Максимальный размер файла: 100 МБ</p>
                </div>
                <Input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  disabled={fileLoading}
                  className="mt-4 max-w-xs mx-auto"
                  ref={fileInputRef}
                />
                {fileLoading && (
                  <div className="mt-4 flex items-center justify-center space-x-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"></div>
                    <span className="text-sm text-muted-foreground">Обработка файла...</span>
                  </div>
                )}
              </div>
              {uploadedFile && !fileError && showSuccess && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="text-green-600" size={20} />
                      <div>
                        <p className="font-medium text-green-800">Файл успешно загружен</p>
                        <p className="text-sm text-green-600">{uploadedFile.name} ({formatFileSize(uploadedFile.size)})</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleClearFile} className="text-gray-600 hover:text-gray-800">Очистить</Button>
                  </div>
                </div>
              )}
              {fileError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="text-red-600" size={20} />
                    <div>
                      <p className="font-medium text-red-800">Ошибка загрузки файла</p>
                      <p className="text-sm text-red-600">{fileError}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          {activeTab === 'file' && previewData && (
            <Card ref={previewRef}>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Eye className="text-primary" size={20} />
                  <span>Предпросмотр данных</span>
                </CardTitle>
                <CardDescription>Первые 5 строк загруженных данных</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border border-border">
                    <thead>
                      <tr className="bg-muted">
                        {previewData.columns.map((column, index) => (
                          <th key={index} className="border border-border p-2 text-left font-medium">{column}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.rows.map((row, rowIndex) => (
                        <tr key={rowIndex} className="hover:bg-muted/50">
                          {row.map((cell, cellIndex) => (
                            <td key={cellIndex} className="border border-border p-2">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-4 flex justify-between items-center">
                  <p className="text-sm text-muted-foreground">
                    Показано {previewData.rows.length} из {previewData.totalRows} строк
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        <TabsContent value="database" className="space-y-6">
          <Card>
            <CardHeader onClick={()=>setCredOpen(prev=>!prev)} className="cursor-pointer select-none space-y-2">
              <div className="w-full flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Database className="text-primary" size={20} />
                  <span>Загрузка из БД</span>
                </div>
                {credOpen ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
              </div>
              <CardDescription>Введите учетные данные для загрузки данных из базы данных</CardDescription>
            </CardHeader>
            {credOpen && (
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Пользователь</Label>
                  <Input id="username" placeholder="postgres" value={localUsername} onChange={e => setLocalUsername(e.target.value)} disabled={dbConnected || dbConnecting} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Пароль</Label>
                  <Input id="password" type="password" placeholder="••••••••" value={localPassword} onChange={e => setLocalPassword(e.target.value)} disabled={dbConnected || dbConnecting} />
                </div>
              </div>
              {!dbConnected ? (
                <Button onClick={handleDbConnect} disabled={dbConnecting || dbConnected || !localUsername || !localPassword} className="w-full">{dbConnecting ? 'Подключение...' : 'Подключиться'}</Button>
              ) : (
                <Button onClick={handleDbDisconnect} className="w-full">Отключиться</Button>
              )}
              {dbSuccess && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="text-green-600" size={20} />
                    <div>
                      <p className="font-medium text-green-800">Подключение успешно</p>
                      <p className="text-sm text-green-600">Соединение с базой данных установлено</p>
                    </div>
                  </div>
                </div>
              )}
              {dbError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="text-red-600" size={20} />
                    <div>
                      <p className="font-medium text-red-800">Ошибка подключения</p>
                      <p className="text-sm text-red-600">{dbError}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
            )}
          </Card>
          {activeTab === 'database' && dbConnected && (
            <Card className="bg-white border border-border rounded-lg">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Database className="text-primary" size={18} />
                  <span>Выбор таблицы из БД</span>
                </CardTitle>
                <CardDescription>Выберите таблицу для загрузки данных</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {dbSuccessLoaded && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                    <CheckCircle className="text-green-600 mx-auto mb-2" size={32} />
                    <div className="font-semibold text-green-800 text-lg">Файл успешно загружен из БД</div>
                  </div>
                )}
                {dbTablesLoading ? (
                  <div className="text-center text-muted-foreground py-4">Загрузка списка таблиц...</div>
                ) : dbTables.length === 0 ? (
                  <div className="text-center text-muted-foreground py-4">Нет доступных таблиц</div>
                ) : (
                  <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className="w-full md:w-1/2">
                      <Label htmlFor="schema-select">Схема</Label>
                      <select id="schema-select" className="block w-full px-3 py-2 mt-1 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-base" value={selectedSchema} onChange={e => {
                        setSelectedSchema(e.target.value);
                        const schemaObj = dbTables.find(s => s.schema === e.target.value);
                        if (schemaObj && schemaObj.tables.length > 0) {
                          setSelectedDbTable('');
                        } else {
                          setSelectedDbTable('');
                        }
                      }}>
                        <option value="">Выберите схему</option>
                        {dbTables.map((s, idx) => (
                          <option key={s.schema + idx} value={s.schema}>{s.schema}</option>
                        ))}
                      </select>
                    </div>
                    <div className="w-full md:w-1/2">
                      <Label htmlFor="table-select">Таблица</Label>
                      <select id="table-select" className="block w-full px-3 py-2 mt-1 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-base" value={selectedDbTable} onChange={e => setSelectedDbTable(e.target.value)} disabled={!selectedSchema || dbTables.length === 0}>
                        <option value="">Выберите таблицу</option>
                        {(() => {
                          const schemaObj = dbTables.find(s => s.schema === selectedSchema);
                          return schemaObj ? schemaObj.tables.map(tbl => (
                            <option key={schemaObj.schema + '.' + tbl} value={tbl}>{tbl}</option>
                          )) : null;
                        })()}
                      </select>
                    </div>
                  </div>
                )}
                {/* Предпросмотр таблицы из БД */}
                {tablePreview && tablePreview.columns && tablePreview.rows && tablePreview.rows.length > 0 && !tablePreviewLoading && !tablePreviewError && (
                  <div className="mt-6">
                    <span className="font-semibold text-lg mb-2 block">Предпросмотр таблицы</span>
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse border border-border rounded-xl overflow-hidden">
                        <thead>
                          <tr className="bg-muted">
                            {tablePreview.columns.map((column, index) => (
                              <th key={index} className="border border-border p-2 text-left font-medium first:rounded-tl-xl last:rounded-tr-xl">{column}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tablePreview.rows.map((row, rowIndex) => (
                            <tr key={rowIndex} className={`hover:bg-muted/50 ${rowIndex === tablePreview.rows.length - 1 ? 'last:rounded-b-xl' : ''}`}>
                              {row.map((cell, cellIndex) => (
                                <td key={cellIndex} className="border border-border p-2 first:rounded-bl-xl last:rounded-br-xl">{cell}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="mt-4 flex justify-between items-center">
                      <p className="text-sm text-muted-foreground">Показано {tablePreview.rows.length} строк</p>
                    </div>
                  </div>
                )}
                {/* Always show buttons, regardless of dbSuccessLoaded or selectedDbTable */}
                <div className="flex justify-end space-x-4 mt-4">
                  <Button variant="outline">Назад</Button>
                  <Button
                    className="bg-primary hover:bg-primary/90"
                    onClick={loadTableFromDb}
                    disabled={!(selectedSchema && selectedDbTable) || tableLoadingFromDb}
                  >
                    {tableLoadingFromDb ? 'Загрузка...' : 'Загрузить таблицу'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}