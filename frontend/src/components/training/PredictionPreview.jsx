import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/card.jsx';
import { Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '../ui/table.jsx';
import { List } from 'lucide-react';

export default function PredictionPreview({ predictionRows }) {
  if (!predictionRows || predictionRows.length === 0) return null;
  const previewRows = predictionRows.slice(0, 5);
  const headers = Object.keys(previewRows[0] || {});

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <List className="text-primary" size={20} />
          <span>Предпросмотр прогноза (первые 5 строк)</span>
        </CardTitle>
        <CardDescription>
          Полный файл с результатами доступен для скачивания после завершения обучения
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              {headers.map((h) => (
                <TableHead key={h}>{h}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {previewRows.map((row, idx) => (
              <TableRow key={idx}>
                {headers.map((h) => (
                  <TableCell key={h}>{row[h]}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
} 