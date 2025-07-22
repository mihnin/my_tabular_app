import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useData } from '../contexts/DataContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { BarChart3, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { API_BASE_URL } from '../apiConfig.js'

export default function Analysis() {
  const navigate = useNavigate();
  const { trainFile, predictFile, predictionProcessed, analysisCache, setAnalysisCache } = useData();
  const [trainResult, setTrainResult] = useState(null);
  const [predictResult, setPredictResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('train');

  // Ключи для кэша
  const { sessionId } = useData(); // глобальный sessionId из DataContext
  const trainCacheKey = sessionId ? `train_session_${sessionId}` : (trainFile ? `train_file_${trainFile.name}_${trainFile.size}` : null);
  const predictCacheKey = sessionId ? `predict_session_${sessionId}` : (predictFile ? `predict_file_${predictFile.name}_${predictFile.size}` : null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError('');
      try {
        const formData = new FormData();
        if (trainFile) formData.append('train_file', trainFile);
        if (predictFile) formData.append('predict_file', predictFile);
        if (sessionId) formData.append('session_id', sessionId);
        const res = await fetch(`${API_BASE_URL}/analyze-tabular`, {
          method: 'POST',
          body: formData
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Ошибка анализа');
        const result = await res.json();
        setTrainResult(result.train);
        setPredictResult(result.predict);
        // Кэшируем
        setAnalysisCache(prev => ({
          ...prev,
          ...(result.train ? { [trainCacheKey]: result.train } : {}),
          ...(result.predict ? { [predictCacheKey]: result.predict } : {})
        }));
      } catch (e) {
        setError(e.message || 'Ошибка анализа файла');
      } finally {
        setLoading(false);
      }
    }
    // Проверяем кэш
    let needLoad = false;
    if (trainCacheKey && analysisCache[trainCacheKey]) {
      setTrainResult(analysisCache[trainCacheKey]);
    } else if (trainCacheKey) {
      needLoad = true;
    }
    if (predictCacheKey && analysisCache[predictCacheKey]) {
      setPredictResult(analysisCache[predictCacheKey]);
    } else if (predictCacheKey) {
      needLoad = true;
    }
    if (needLoad) loadData();
    // eslint-disable-next-line
  }, [trainFile, predictFile, sessionId]);

  // Сброс кэша при загрузке новых файлов
  useEffect(() => {
    if (!trainFile && !sessionId && !predictFile) {
      setAnalysisCache({});
    }
  }, [trainFile, sessionId, predictFile]);

  const current = activeTab === 'train' ? trainResult : predictResult;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">Анализ данных</h1>
        <p className="text-muted-foreground">Обзор пропусков по каждому столбцу для train и prediction файлов</p>
      </div>
      <div className="mb-4 flex gap-4">
        <Button variant={activeTab === 'train' ? 'default' : 'outline'} onClick={() => setActiveTab('train')}>Train файл</Button>
        <Button variant={activeTab === 'predict' ? 'default' : 'outline'} onClick={() => setActiveTab('predict')}>Prediction файл</Button>
      </div>
      {loading ? <div>Загрузка...</div> : error ? <div className="text-red-500">{error}</div> : (
        <div className="space-y-6">
          {current ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <BarChart3 className="text-primary" size={20} />
                      <span>Всего записей</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-primary">{current.total}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <AlertTriangle className="text-orange-500" size={20} />
                      <span>Всего пропусков</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-orange-600">{current.missing_by_column ? current.missing_by_column.reduce((sum, col) => sum + col.missing, 0) : 0}</div>
                  </CardContent>
                </Card>
              </div>
              <Card>
                <CardHeader>
                  <CardTitle>Пропуски по столбцам</CardTitle>
                </CardHeader>
                <CardContent style={{ height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={current.missing_by_column || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="column" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="missing" fill="#f59e42" name="Пропуски" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </>
          ) : <div>Нет данных для анализа</div>}
          <div className="flex justify-between items-center mt-8">
            <Button
              variant="outline"
              onClick={() => navigate('/training')}
            >
              Назад к обучению
            </Button>
            <Button
              variant="default"
              onClick={() => navigate('/export')}
              disabled={!predictionProcessed}
              title={predictionProcessed ? '' : 'Сначала выполните прогнозирование'}
            >
              Перейти к экспорту
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

