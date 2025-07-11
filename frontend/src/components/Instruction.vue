<template>
  <div v-if="isVisible" class="instruction-block">
    <div class="excel-format-info" style="margin-bottom:1rem;">
      <h2 style="margin-top:0;">Требования к формату Excel для обучения</h2>
      <ul>
        <li>Данные для обучения должны быть размещены <b>на первом листе</b> Excel-файла.</li>
        <li>В <b>первой строке</b> должны быть указаны <b>названия всех колонок</b> (features и целевая переменная).</li>
        <li>Данные должны начинаться <b>со второй строки</b> (первая строка — только заголовки).</li>
        <li>В каждой колонке должны быть значения одного типа (числа, строки, даты и т.д.).</li>
        <li>Не допускается наличие объединённых ячеек, скрытых строк/столбцов, формул и других листов с данными.</li>
        <li>Файл не должен содержать пустых строк между заголовком и данными.</li>
        <li>Рекомендуется использовать расширения <b>.xlsx</b> или <b>.xls</b>.</li>
      </ul>
    </div>
    <div class="excel-files-info" style="margin-bottom:2.5rem;">
      <h3>Файл для обучения</h3>
      <ul>
        <li>Должен содержать <b>все признаки (features)</b> и <b>целевую переменную</b> (target).</li>
        <li>В каждой строке должны быть заполнены значения и для признаков, и для целевой переменной.</li>
        <li>Целевая переменная должна быть указана в первой строке (заголовке) вместе с остальными колонками.</li>
      </ul>
      <h3>Файл для прогноза</h3>
      <ul>
        <li>Должен содержать <b>те же признаки (features)</b>, что и файл для обучения.</li>
        <li>Колонка с целевой переменной <b>может отсутствовать</b> или быть <b>пустой</b> (без значений).</li>
        <li>Порядок и названия колонок должны совпадать с файлом для обучения (кроме целевой переменной).</li>
      </ul>
      <div style="display:flex; gap:1rem; flex-wrap:wrap; margin-top:1.2rem;">
        <button class="example-btn" @click="downloadExample('train')">Скачать пример данных для обучения</button>
        <button class="example-btn" @click="downloadExample('predict')">Скачать пример данных для прогноза</button>
      </div>
    </div>
    <h2>Инструкция по обучению и прогнозу на табличных данных</h2>
    <div class="instruction-steps">
      <div class="step">
        <h3>1. Подключение к базе данных (необязательно)</h3>
        <p>
          Для того чтобы загружать данные из приложения в базу данных или из базы данных в приложение, нужно подключиться к БД. Для этого нажмите на кнопку с иконкой базы данных в верхнем правом углу экрана и введите свой логин и пароль Postgres.
        </p>
      </div>
      <div class="step">
        <h3>2. Загрузка данных для обучения и прогноза</h3>
        <p>Для обучения и прогноза необходимо выбрать два файла одним из двух способов:</p>
        <ul>
          <li>
            <b>С личного компьютера:</b> Нажмите "Выбрать файл", выберите файл в файловой системе и нажмите "Загрузить данные из файла".
          </li>
          <li>
            <b>Из базы данных:</b> После подключения к БД появится опция "Загрузить данные из БД". Нажмите на неё, выберите схему и таблицу, из которой хотите загрузить данные.
          </li>
        </ul>
      </div>
      <div class="step">
        <h3>3. Выбор целевой колонки и типа задачи</h3>
        <p>
          <b>Обязательно выберите целевую колонку</b> для обучения модели.<br>
          Также выберите <b>тип задачи</b> из списка:
        </p>
        <ul>
          <li><b>auto</b> — автоматическое определение типа задачи (рекомендуется, если не уверены).</li>
          <li><b>binary</b> — задача бинарной классификации (2 класса, например: да/нет, 0/1).</li>
          <li><b>multiclass</b> — задача многоклассовой классификации (3 и более классов, например: A/B/C).</li>
          <li><b>regression</b> — задача регрессии (прогнозирование числового значения, например: цена, количество).</li>
        </ul>
      </div>
      <div class="step">
        <h3>4. Дополнительные настройки (необязательно)</h3>
        <ul>
          <li><b>Обработка пропусков:</b> По умолчанию выбран способ "mean" — все пропущенные значения будут заполнены средними значениями.</li>
          <li><b>Метрика:</b> Выберите метрику, по которой будет обучаться модель.<br>
            <span style="font-size:0.97em; color:#444;">
              <b>Краткое описание метрик:</b><br>
              <b>Классификация (binary, multiclass):</b>
              <ul>
                <li><b>accuracy</b> — доля правильных ответов.</li>
                <li><b>balanced_accuracy</b> — accuracy, скорректированная для несбалансированных классов.</li>
                <li><b>roc_auc</b> — площадь под ROC-кривой (только для binary).</li>
                <li><b>f1</b> — гармоническое среднее precision и recall.</li>
                <li><b>precision</b> — точность (доля истинно положительных среди предсказанных положительных).</li>
                <li><b>recall</b> — полнота (доля истинно положительных среди всех фактических положительных).</li>
                <li><b>log_loss</b> — логарифмическая функция потерь (чем меньше, тем лучше).</li>
                <li><b>average_precision</b> — средняя точность по всем порогам (только для binary).</li>
              </ul>
              <b>Регрессия (regression):</b>
              <ul>
                <li><b>root_mean_squared_error</b> — корень из среднеквадратичной ошибки (RMSE).</li>
                <li><b>mean_squared_error</b> — среднеквадратичная ошибка (MSE).</li>
                <li><b>mean_absolute_error</b> — средняя абсолютная ошибка (MAE).</li>
                <li><b>r2</b> — коэффициент детерминации (R², чем ближе к 1, тем лучше).</li>
                <li><b>pearsonr</b> — коэффициент корреляции Пирсона.</li>
                <li><b>spearmanr</b> — коэффициент ранговой корреляции Спирмена.</li>
              </ul>
              <b>auto</b> — доступны все метрики, подходящие под задачу.
            </span>
          </li>
          <li><b>Модели:</b> Выберите модели для обучения.</li>
          <li><b>Пресет AutoGluon:</b> Выберите один из пресетов, который определяет стратегию обучения моделей:
            <ul>
              <li><b>medium_quality</b> — баланс между скоростью и качеством.</li>
              <li><b>good_quality</b> — хорошее качество, чуть дольше по времени.</li>
              <li><b>high_quality</b> — высокое качество, дольше по времени. <span style="color:#388e3c;font-weight:600;">Рекомендуется</span></li>
              <li><b>best_quality</b> — максимальное качество, максимальное время.</li>
              <li><b>optimize_for_deployment</b> — оптимизация для развёртывания (быстрые и компактные модели).</li>
              <li><b>experimental</b> — экспериментальные настройки (может быть нестабильно).</li>
            </ul>
          </li>
          <li><b>Лимит времени:</b> Установите лимит времени на обучение моделей. Лучше всего не ограничивать по времени для получения наилучших результатов.</li>
        </ul>
      </div>
      <div class="step">
        <h3>5. Запуск обучения и прогнозирования</h3>
        <p>
          Нажмите кнопку <b>"Начать обучение"</b>. Если выбрана опция <b>"Обучение, сохранение и прогноз"</b>, после обучения автоматически будет сделан прогноз, который можно загрузить в базу данных или скачать в виде Excel/CSV.
        </p>
        <div class="tip">
          <b>💡 Совет:</b> Если включено автоматическое сохранение прогноза в БД и выбрана таблица, то после нажатия "Начать обучение" можно закрыть страницу — приложение отработает и сохранит результат в БД. Позже вы сможете скачать результат из базы данных через приложение.
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import type { PropType } from 'vue'
import { BACKEND_URL } from '../apiConfig'
export default defineComponent({
  name: 'Instruction',
  props: {
    isVisible: {
      type: Boolean as PropType<boolean>,
      required: true
    }
  },
  emits: ['close'],
  methods: {
    downloadExample(type: 'train' | 'predict') {
      let url = ''
      if (type === 'train') {
        url = `${BACKEND_URL}/instruction/example_train.xlsx`
      } else {
        url = `${BACKEND_URL}/instruction/example_predict.xlsx`
      }
      // Новый способ скачивания без открытия вкладки
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', '')
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }
})
</script>

<style scoped>
.instruction-block {
  background: #fff;
  padding: 2rem;
  border-radius: 8px;
  width: 100%;
  margin: 0 0 2rem 0;
  box-shadow: 0 2px 16px rgba(0,0,0,0.08);
  max-width: none;
}

.instruction-steps {
  margin-top: 1rem;
}

.step {
  margin-bottom: 2rem;
  padding: 1.5rem;
  border-left: 4px solid #4CAF50;
  background: #f8f9fa;
  border-radius: 0 8px 8px 0;
}

.step h3 {
  color: #2c3e50;
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.step p {
  margin: 0 0 0.5rem 0;
  line-height: 1.6;
  color: #555;
}

.step ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.step li {
  margin-bottom: 0.5rem;
  line-height: 1.5;
  color: #555;
}

.tip {
  background: #e8f5e8;
  border: 1px solid #4CAF50;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 1rem;
  color: #2d5016;
}

.tip b {
  color: #1b5e20;
}

.excel-format-info {
  margin-top: 1rem;
}

.example-btn {
  background: #007bff;
  color: #fff;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.example-btn:disabled {
  background: #007bff;
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .instruction-block {
    padding: 1rem;
  }
  
  .step {
    padding: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .step h3 {
    font-size: 1.1rem;
  }
}
</style>
