import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useData } from '../contexts/DataContext'
import { parseFile } from '../utils/fileParser'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { BarChart3, AlertTriangle, PieChart } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'

export default function Analysis() {
  const navigate = useNavigate();
  const { trainFile, predictFile, trainData, predictData, predictionProcessed } = useData();
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [missingStats, setMissingStats] = useState({ total: 0, missing: 0, percent: 0 });
  const [missingByColumn, setMissingByColumn] = useState([]);
  const [activeTab, setActiveTab] = useState('train');

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError('');
      let data = null;
      if (activeTab === 'train') {
        data = trainData;
        if (!data && trainFile) {
          data = await parseFile(trainFile);
        }
      } else {
        data = predictData;
        if (!data && predictFile) {
          data = await parseFile(predictFile);
        }
      }
      if (!data || !data.rows || !data.columns) {
        setError('Нет данных для анализа');
        setLoading(false);
        return;
      }
      setColumns(data.columns);
      setRows(data.rows);
      // Анализ пропусков по столбцам
      const missingByCol = data.columns.map((col, idx) => {
        let missing = 0;
        for (let row of data.rows) {
          if (row[idx] === '' || row[idx] === null || row[idx] === undefined) missing++;
        }
        return { column: col, missing };
      });
      setMissingByColumn(missingByCol);
      // Общая статистика
      let totalCells = data.rows.length * data.columns.length;
      let missingCells = missingByCol.reduce((sum, col) => sum + col.missing, 0);
      setMissingStats({
        total: data.rows.length,
        missing: missingCells,
        percent: totalCells ? (missingCells / totalCells) * 100 : 0
      });
      setLoading(false);
    }
    loadData();
  }, [trainFile, predictFile, trainData, predictData, activeTab]);

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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="text-primary" size={20} />
                  <span>Всего записей</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{missingStats.total}</div>
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
                <div className="text-2xl font-bold text-orange-600">{missingStats.missing}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <PieChart className="text-blue-400" size={20} />
                  <span>Процент пропусков</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">{missingStats.percent.toFixed(2)}%</div>
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Пропуски по столбцам</CardTitle>
            </CardHeader>
            <CardContent style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={missingByColumn}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="column" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="missing" fill="#f59e42" name="Пропуски" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
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

