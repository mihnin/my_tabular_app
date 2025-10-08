import ExcelJS from 'exceljs';

/**
 * Читает Excel файл и возвращает данные первого листа в виде массива массивов (rows)
 * @param {File|Blob} file - Excel файл
 * @returns {Promise<Array<Array>>} - Массив строк, где первая строка - заголовки
 */
export async function readExcelFile(file) {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const workbook = new ExcelJS.Workbook();
    await workbook.xlsx.load(arrayBuffer);
    
    const worksheet = workbook.worksheets[0];
    if (!worksheet) {
      return [];
    }
    
    const rows = [];
    worksheet.eachRow({ includeEmpty: false }, (row) => {
      rows.push(row.values.slice(1)); // ExcelJS добавляет undefined в начало, убираем его
    });
    
    return rows;
  } catch (error) {
    console.error('Error reading Excel file:', error);
    throw error;
  }
}

/**
 * Извлекает заголовки колонок из Excel файла
 * @param {File|Blob} file - Excel файл
 * @returns {Promise<Array<string>>} - Массив названий колонок
 */
export async function extractColumnsFromExcel(file) {
  if (!file) return [];
  
  try {
    const rows = await readExcelFile(file);
    if (rows.length > 0) {
      return rows[0].map(h => h?.toString().trim());
    }
  } catch (error) {
    console.error('Error extracting columns:', error);
  }
  
  return [];
}

/**
 * Создает Excel файл из массива объектов
 * @param {Array<Object>} data - Массив объектов с данными
 * @param {string} sheetName - Название листа
 * @returns {Promise<Blob>} - Blob с Excel файлом
 */
export async function createExcelFile(data, sheetName = 'Sheet1') {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet(sheetName);
  
  if (data.length === 0) {
    return new Blob([], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  }
  
  // Получаем заголовки из первого объекта
  const headers = Object.keys(data[0]);
  worksheet.addRow(headers);
  
  // Добавляем данные
  data.forEach(item => {
    const row = headers.map(header => item[header]);
    worksheet.addRow(row);
  });
  
  const buffer = await workbook.xlsx.writeBuffer();
  return new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

/**
 * Конвертирует массив массивов в массив объектов
 * @param {Array<Array>} rows - Массив строк (первая строка - заголовки)
 * @returns {Array<Object>} - Массив объектов
 */
export function rowsToObjects(rows) {
  if (rows.length < 2) return [];
  
  const headers = rows[0];
  return rows.slice(1).map(row => {
    const obj = {};
    headers.forEach((header, index) => {
      obj[header] = row[index];
    });
    return obj;
  });
}
