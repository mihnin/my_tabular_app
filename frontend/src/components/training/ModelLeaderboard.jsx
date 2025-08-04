import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/card.jsx';
import { Award } from 'lucide-react';

export default function ModelLeaderboard({
  leaderboard,
  trainingParams,
  trainingConfig,
  formatCellValue
}) {
  if (!leaderboard || leaderboard.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Award className="text-primary" size={20} />
          <span>Лидерборд моделей</span>
        </CardTitle>
        <CardDescription>
          Сравнение качества обученных моделей по различным метрикам
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                {Object.keys(leaderboard[0]).map((key) => (
                  <th key={key} className="text-left p-3 font-medium">
                    {key === 'rank' ? 'Ранг' :
                     key === 'model' ? 'Модель' :
                     key === 'status' ? 'Статус' :
                     key === 'mae' ? 'MAE' :
                     key === 'mape' ? 'MAPE' :
                     key === 'rmse' ? 'RMSE' :
                     key === 'r2' || key === 'rsquared' ? 'R²' :
                     key === 'trainingTime' || key === 'training_time' ? 'Время' :
                     key === 'score_val' ? (trainingParams?.evaluation_metric || trainingConfig?.selectedMetric || 'Метрика') :
                     key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leaderboard
                .sort((a, b) => (a.rank || 999) - (b.rank || 999))
                .map((row, index) => (
                <tr 
                  key={index} 
                  className={`border-b hover:bg-muted/50`}
                >
                  {Object.entries(row).map(([key, value]) => (
                    <td key={key} className="p-3">
                      {formatCellValue(key, value)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}