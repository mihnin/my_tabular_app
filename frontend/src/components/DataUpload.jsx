import React from 'react';
import { useData } from '../contexts/DataContext';
import SingleDataUpload from './SingleDataUpload';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button.jsx';

export default function DataUpload() {
  React.useEffect(() => {
    document.title = 'Прогнозирование табличных данных';
  }, []);

  const {
    // Train
    trainData, setTrainData, trainFile, setTrainFile, trainSource, setTrainSource,
    // Predict
    predictData, setPredictData, predictFile, setPredictFile, predictSource, setPredictSource,
    // Shared DB/file state for train
    authToken, setAuthToken,
    dbConnected, setDbConnected,
    dbTables, setDbTables,
    dbTablesLoading, setDbTablesLoading,
    dbError, setDbError,
    // For train
    trainActiveTab, setTrainActiveTab,
    trainPreviewData, setTrainPreviewData,
    trainSelectedDbTable, setTrainSelectedDbTable,
    trainSelectedSchema, setTrainSelectedSchema,
    trainTablePreview, setTrainTablePreview,
    updateTrainData,
    // For predict
    predictActiveTab, setPredictActiveTab,
    predictPreviewData, setPredictPreviewData,
    predictSelectedDbTable, setPredictSelectedDbTable,
    predictSelectedSchema, setPredictSelectedSchema,
    predictTablePreview, setPredictTablePreview,
    updatePredictData,
  } = useData();

  const navigate = useNavigate();
  const bothFilesUploaded = Boolean(trainFile && predictFile);

  // Используем глобальные состояния вместо локальных
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <SingleDataUpload
        title="Данные для обучения"
        description="Загрузите таблицу для обучения модели (train set) из файла или из БД."
        uploadedFile={trainFile}
        setUploadedFile={setTrainFile}
        previewData={trainPreviewData}
        setPreviewData={setTrainPreviewData}
        activeTab={trainActiveTab}
        setActiveTab={setTrainActiveTab}
        dbConnected={dbConnected}
        setDbConnected={setDbConnected}
        dbTables={dbTables}
        setDbTables={setDbTables}
        dbTablesLoading={dbTablesLoading}
        setDbTablesLoading={setDbTablesLoading}
        dbError={dbError}
        setDbError={setDbError}
        authToken={authToken}
        setAuthToken={setAuthToken}
        selectedDbTable={trainSelectedDbTable}
        setSelectedDbTable={setTrainSelectedDbTable}
        selectedSchema={trainSelectedSchema}
        setSelectedSchema={setTrainSelectedSchema}
        tablePreview={trainTablePreview}
        setTablePreview={setTrainTablePreview}
        updateData={updateTrainData}
        mode="train"
      />
      <SingleDataUpload
        title="Данные для прогноза"
        description="Загрузите таблицу для прогноза (predict set) из файла или из БД."
        uploadedFile={predictFile}
        setUploadedFile={setPredictFile}
        previewData={predictPreviewData}
        setPreviewData={setPredictPreviewData}
        activeTab={predictActiveTab}
        setActiveTab={setPredictActiveTab}
        dbConnected={dbConnected}
        setDbConnected={setDbConnected}
        dbTables={dbTables}
        setDbTables={setDbTables}
        dbTablesLoading={dbTablesLoading}
        setDbTablesLoading={setDbTablesLoading}
        dbError={dbError}
        setDbError={setDbError}
        authToken={authToken}
        setAuthToken={setAuthToken}
        selectedDbTable={predictSelectedDbTable}
        setSelectedDbTable={setPredictSelectedDbTable}
        selectedSchema={predictSelectedSchema}
        setSelectedSchema={setPredictSelectedSchema}
        tablePreview={predictTablePreview}
        setTablePreview={setPredictTablePreview}
        updateData={updatePredictData}
        mode="predict"
      />
      <div className="flex justify-end items-center mt-8 gap-4">
        {bothFilesUploaded && (
          <>
            <Button
              variant="outline"
              onClick={() => navigate('/')}
            >
              Назад
            </Button>
            <Button
              className="bg-primary text-white"
              onClick={() => navigate('/config')}
            >
              Продолжить к настройке модели
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

