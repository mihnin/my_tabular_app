<template>
  <div class="training" v-if="isVisible">
    <h3 class="section-title">Обучение модели</h3>
    
    <!-- Чекбокс для комплексного действия -->
    <div class="training-checkbox">
      <label>
        <input 
          type="checkbox" 
          v-model="trainPredictSave"
        > Обучить и сделать прогноз
      </label>
    </div>

    <!-- Новая кнопка автосохранения в БД -->
    <div v-if="showAutoSaveButton" style="margin-bottom: 16px; text-align: left;">
      <button 
        class="train-button" 
        style="margin-top:0; width:100%; min-width:unset; display:flex; align-items:center; justify-content:center; gap:8px;"
        :disabled="!canAutoSaveToDb"
        @click="openAutoSaveModal"
      >
        <svg xmlns="http://www.w3.org/2000/svg" height="20" viewBox="0 0 20 20" width="20" style="vertical-align:middle;"><g><ellipse cx="10" cy="5.5" rx="8" ry="3.5" fill="#fff" stroke="#007bff" stroke-width="1.2"/><ellipse cx="10" cy="5.5" rx="8" ry="3.5" fill="#007bff" fill-opacity=".15"/><rect x="2" y="5.5" width="16" height="7" rx="4" fill="#fff" stroke="#007bff" stroke-width="1.2"/><rect x="2" y="5.5" width="16" height="7" rx="4" fill="#007bff" fill-opacity=".10"/><rect x="2" y="12.5" width="16" height="3" rx="1.5" fill="#fff" stroke="#007bff" stroke-width="1.2"/><rect x="2" y="12.5" width="16" height="3" rx="1.5" fill="#007bff" fill-opacity=".10"/></g></svg>
        Автоматическое сохранение прогноза в БД
      </button>
    </div>

    <!-- Блок с прогрессом обучения -->
    <div v-if="trainingStatus" class="training-status">
      <div class="progress-container">
        <div 
          class="progress-bar" 
          :style="{ width: `${trainingStatus.progress}%` }"
          :class="{ 'progress-error': trainingStatus.status === 'failed' }"
        ></div>
      </div>
      <div class="status-text">
        {{ getStatusMessage }}
      </div>
      <div v-if="trainingStatus.status === 'failed'" class="error-message">
        {{ trainingStatus.error }}
      </div>
    </div>

    <!-- Кнопка обучения -->
    <button 
      @click="startTraining"
      class="train-button"
      :disabled="!canStartTraining || isTraining"
    >
     {{ buttonText }}
    </button>

    <!-- Модальное окно для автосохранения в БД -->
    <Teleport to="body">
      <div v-if="autoSaveModalVisible" class="db-modal-overlay" @click="closeAutoSaveModal">
        <div class="db-modal upload-to-db-modal" id="auto-save-db-modal" @click.stop style="max-width:420px;min-width:320px;min-height:220px;box-sizing:border-box;font-size:0.98rem;">
          <button class="close-btn" @click="closeAutoSaveModal">×</button>
          <h3 style="margin-bottom:1rem">Сохранить прогноз в БД</h3>
          <div style="margin-bottom:1rem; display:flex; gap:1.5rem; align-items:center;">
            <label style="display:flex; align-items:center; gap:6px; font-weight:500;">
              <input type="radio" value="new" v-model="dbSaveMode" />
              Создать новую таблицу
            </label>
            <label style="display:flex; align-items:center; gap:6px; font-weight:500;">
              <input type="radio" value="existing" v-model="dbSaveMode" />
              Загрузить в существующую
            </label>
          </div>
          <!-- Новая таблица -->
          <div v-if="dbSaveMode === 'new'">
            <!-- Выбор схемы для новой таблицы -->
            <div>
              <label class="input-label">Выберите схему:</label>
              <select v-model="selectedDbSchema" class="db-input">
                <option v-for="schema in dbSchemas" :key="schema" :value="schema">{{ schema }}</option>
              </select>
            </div>
            <!-- Название таблицы -->
            <div style="margin-top:0.7rem;">
              <label class="input-label">Название таблицы:</label>
              <input v-model="newTableName" class="db-input db-input-full" placeholder="Введите название таблицы" />
            </div>
            <div v-if="tableData && tableData.length" style="margin-bottom:1rem;">
              <label class="input-label primary-keys-label" style="font-weight:500; color:#333; margin-bottom:0.5rem; display:block; margin-top:1.2rem;">
                Выберите первичные ключи (опционально):
              </label>
              <div style="display:flex; flex-wrap:wrap; gap:8px;">
                <label v-for="col in Object.keys(tableData[0])" :key="col" style="display:flex; align-items:center; gap:4px;">
                  <input type="checkbox" :value="col" v-model="selectedPrimaryKeys" />
                  <span>{{ col }}</span>
                </label>
              </div>
            </div>
          </div>
          <!-- Существующая таблица -->
          <div v-if="dbSaveMode === 'existing'">
            <!-- Выбор схемы для существующей таблицы -->
            <div style="margin-bottom: 1rem;">
              <label class="input-label" style="display:block; margin-bottom:0.5rem;">
                Выберите схему:
              </label>
              <select v-model="selectedDbSchema" class="db-input" style="width:100%;margin-bottom:1rem;">
                <option v-for="schema in dbSchemas" :key="schema" :value="schema">{{ schema }}</option>
              </select>
            </div>
            <label class="input-label" style="display:block; margin-bottom:0.5rem;">Выберите таблицу:</label>
            <div v-if="dbTableCountAvailable !== null && dbTableCountTotal !== null" class="table-count-info">
              Доступно {{ dbTableCountAvailable }} таблиц из {{ dbTableCountTotal }}
            </div>
            <!-- Выпадающий список для выбора таблицы -->
            <select v-model="selectedTable" class="db-input db-input-full" style="margin-bottom:1rem;">
              <option value="" disabled selected>Загрузка списка...</option>
              <option v-for="table in filteredDbTables" :key="table" :value="table">{{ table }}</option>
            </select>
          </div>
          <div class="upload-to-db-footer">
            <button class="upload-to-db-btn" :disabled="(dbSaveMode==='new' && !newTableName) || (dbSaveMode==='existing' && !selectedTable) || dbLoading" @click="handleSaveToDb">
              <span v-if="dbLoading" class="spinner-wrap"><span class="spinner"></span></span>
              Сохранить в эту таблицу после обучения
            </button>
            <div v-if="dbError" class="error-message upload-to-db-error-area">{{ dbError }}</div>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- Модальное окно успешного сохранения -->
    <Teleport to="body">
      <div v-if="saveSuccessModalVisible" class="success-modal-overlay">
        <div class="success-modal">
          <div class="success-icon">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#4CAF50"/>
              <path d="M24 42L36 54L56 34" stroke="white" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="success-text">Изменения сохранены</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, ref, watch } from 'vue'
import { useMainStore } from '../stores/mainStore'

export default defineComponent({
  name: 'Training',
  
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },

  setup() {
    const store = useMainStore()
    let statusCheckInterval: number | null = null

    const trainPredictSave = computed({
      get: () => store.trainPredictSave,
      set: (value: boolean) => store.setTrainPredictSave(value)
    })

    const showAutoSaveButton = computed(() => {
      return store.dbConnected && trainPredictSave.value
    })
    const canAutoSaveToDb = computed(() => {
      return (
        store.targetColumn !== '<нет>' &&
        store.selectedFile !== null &&
        store.selectedTestFile !== null &&
        store.dbConnected
      )
    })
    const isTraining = computed(() => {
      return store.trainingStatus && ['initializing', 'running'].includes(store.trainingStatus.status)
    })
    const buttonText = computed(() => {
      if (!isTraining.value) return '🚀 Начать обучение'
      return '⏳ Обучение...'
    })
    const getStatusMessage = computed(() => {
      if (!store.trainingStatus) return ''
      // Show special message if pycaret_locked is True
      if (store.trainingStatus.pycaret_locked === true) {
        return 'Повышеная нагрузка на сервер. Обучение и прогноз займет немного больше времени.'
      }
      const status = store.trainingStatus.status
      if (status === 'initializing') return 'Инициализация обучения...'
      if (status === 'running') return `Обучение в процессе (${store.trainingStatus.progress ?? 0}%)`
      if (status === 'completed') return 'Обучение успешно завершено!'
      if (status === 'failed') return 'Ошибка при обучении'
      return status
    })
    const canStartTraining = computed(() => {
      return store.selectedFile !== null &&
             store.selectedTestFile !== null &&
             store.targetColumn !== '<нет>' &&
             !isTraining.value
    })

    // --- Модальное окно автосохранения в БД ---
    const autoSaveModalVisible = ref(false)
    const dbTableNames = ref<string[]>([])
    const dbLoading = ref(false)
    const dbError = ref('')
    const selectedTable = ref<string>('')
    const newTableName = ref<string>('')
    const dbTableCountAvailable = ref<number|null>(null)
    const dbTableCountTotal = ref<number|null>(null)
    const dbSaveMode = ref<'new' | 'existing'>('new')
    const selectedPrimaryKeys = ref<string[]>([])
    const predictionRows = computed(() => store.predictionRows)
    const tableData = computed(() => store.tableData)
    const dbSchemas = ref<string[]>([])
    const selectedDbSchema = ref('')
    const dbTablesBySchema = ref<{[schema: string]: string[]}>({})
    const filteredDbTables = computed(() => {
      if (!selectedDbSchema.value) return []
      return dbTablesBySchema.value[selectedDbSchema.value] || []
    })
    
    // Для авторизации используем store.authToken
    const dbToken = computed(() => store.authToken || '')

    const openAutoSaveModal = async () => {
      autoSaveModalVisible.value = true
      dbLoading.value = true
      dbError.value = ''
      selectedTable.value = ''
      newTableName.value = ''
      dbTableCountAvailable.value = null
      dbTableCountTotal.value = null
      try {
        const resp = await fetch('http://localhost:8000/get-tables', {
          headers: {
            'Authorization': `Bearer ${dbToken.value}`
          }
        })
        if (!resp.ok) throw new Error('Ошибка загрузки таблиц')
        const data = await resp.json()
        dbSchemas.value = Object.keys(data.tables)
        dbTablesBySchema.value = data.tables
        selectedDbSchema.value = dbSchemas.value[0] || ''
        dbTableNames.value = []
        dbTableCountAvailable.value = data.count_available ?? 0
        dbTableCountTotal.value = data.count_total ?? 0
      } catch (e: any) {
        dbError.value = e.message || 'Ошибка'
        dbSchemas.value = []
        dbTablesBySchema.value = {}
        dbTableNames.value = []
        dbTableCountAvailable.value = null
        dbTableCountTotal.value = null
      } finally {
        dbLoading.value = false
      }
    }
    const closeAutoSaveModal = () => {
      autoSaveModalVisible.value = false
    }

    const checkTrainingStatus = async () => {
      if (!store.sessionId) return
      try {
        const response = await fetch(`http://localhost:8000/training_status/${store.sessionId}`)
        if (!response.ok) {
          throw new Error('Failed to fetch training status')
        }
        const status = await response.json()
        if (status.progress === 100) {
          console.log('=== TRAINING COMPLETE ===', status)
        }
        store.setTrainingStatus(status)
        // --- ДОБАВЛЕНО: если есть prediction_head, обновить predictionRows ---
        if (status.prediction_head && Array.isArray(status.prediction_head) && status.prediction_head.length > 0) {
          store.setPredictionRows(status.prediction_head)
        }
        if (["completed", "failed", "complete"].includes(status.status)) {
          if (statusCheckInterval) {
            clearInterval(statusCheckInterval)
            statusCheckInterval = null
          }
        }
      } catch (error) {
        console.error('Error checking training status:', error)
      }
    }

    const startTraining = async () => {
      try {
        // Сброс статусов
        store.setTrainingStatus(null)
        store.setPredictionRows([])
        store.setSessionId(null)
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval)
          statusCheckInterval = null
        }
        store.setTrainingStatus({ status: 'initializing', progress: 0 })

        // Проверка наличия train файла
        if (!store.selectedFile) {
          alert('Ошибка: Файл не выбран. Пожалуйста, загрузите файл перед обучением модели.');
          store.setTrainingStatus(null);
          return;
        }
        // Проверка расширения файла
        const allowedExt = /\.(csv|xlsx|xls)$/i;
        if (!allowedExt.test(store.selectedFile.name)) {
          alert('Файл должен быть в формате CSV или Excel (.csv, .xlsx, .xls)');
          store.setTrainingStatus(null);
          return;
        }
        // Формируем параметры для табличной задачи
        const params: Record<string, any> = {
          target_column: store.targetColumn,
          problem_type: store.problemType,
          evaluation_metric: store.selectedMetric, // только из store
          autogluon_preset: store.selectedPreset,
          models_to_train: store.selectedModels,
          fill_missing_method: store.fillMethod,
          training_time_limit: store.timeLimit,
        };
        // --- ДОБАВЛЯЕМ upload_table_name и upload_table_schema в params, если автосохранение ---
        if (
          trainPredictSave.value &&
          dbSaveMode.value &&
          selectedDbSchema.value
        ) {
          params.upload_table_schema = selectedDbSchema.value;
          if (dbSaveMode.value === 'existing' && selectedTable.value) {
            params.upload_table_name = selectedTable.value;
          }
          if (dbSaveMode.value === 'new' && newTableName.value) {
            params.upload_table_name = newTableName.value.trim();
          }
        }
        const formData = new FormData();
        formData.append('params', JSON.stringify(params));
        formData.append('train_file', store.selectedFile, store.selectedFile.name);
        if (store.selectedTestFile) {
          formData.append('test_file', store.selectedTestFile, store.selectedTestFile.name);
        }
        // --- ДОБАВЛЯЕМ схему и таблицу для автосохранения, если нужно (legacy, можно убрать) ---
        if (
          trainPredictSave.value &&
          dbSaveMode.value === 'existing' &&
          selectedTable.value &&
          selectedDbSchema.value
        ) {
          formData.append('db_table', selectedTable.value);
          formData.append('db_schema', selectedDbSchema.value);
        }
        // --- ЯВНО ДОБАВЛЯЕМ db_schema для новой таблицы ---
        if (
          trainPredictSave.value &&
          dbSaveMode.value === 'new' &&
          newTableName.value &&
          selectedDbSchema.value
        ) {
          formData.append('db_schema', selectedDbSchema.value);
        }
        // Выбор эндпоинта в зависимости от чекбокса
        const endpoint = trainPredictSave.value
          ? 'http://localhost:8000/train_prediction_save/'
          : 'http://localhost:8000/train_tabular';
        // --- Добавляем headers с токеном, если есть ---
        const headers: Record<string, string> = { 'Accept': 'application/json' };
        if (trainPredictSave.value && dbToken.value) {
          headers['Authorization'] = `Bearer ${dbToken.value}`;
        }
        // Отправляем запрос на backend
        const response = await fetch(endpoint, {
          method: 'POST',
          body: formData,
          headers
        });
        if (!response.ok) {
          const errorText = await response.text();
          let errorData;
          try { errorData = JSON.parse(errorText); } catch (e) { errorData = { detail: errorText }; }
          const errorMessage = errorData.detail || 'Failed to train model';
          alert(`Ошибка обучения: ${errorMessage}`);
          store.setTrainingStatus({ status: 'failed', progress: 0, error: errorMessage });
          return;
        }
        const result = await response.json();
        store.setSessionId(result.session_id)
        store.setTrainingStatus({ status: 'running', progress: 0 })
        // Запускаем опрос статуса
        statusCheckInterval = setInterval(checkTrainingStatus, 2000) as unknown as number
      } catch (error) {
        alert('Произошла ошибка при обучении модели. Подробности в консоли.');
        store.setTrainingStatus({ status: 'failed', progress: 0, error: error instanceof Error ? error.message : 'Неизвестная ошибка' });
      }
    }

    // --- Создание таблицы в БД по первой строке файла ---
    const createTableFromFile = async () => {
      if (!newTableName.value || !store.selectedFile) return;
      dbLoading.value = true;
      dbError.value = '';
      try {
        const formData = new FormData();
        formData.append('file', store.selectedFile as Blob, store.selectedFile?.name ?? 'uploaded_file');
        formData.append('table_name', newTableName.value);
        formData.append('primary_keys', JSON.stringify(selectedPrimaryKeys.value));
        // Специальный режим: только создание таблицы по первой строке
        formData.append('create_table_only', 'true');
        formData.append('db_schema', selectedDbSchema.value); // <-- исправлено
        const resp = await fetch('http://localhost:8000/create-table-from-file', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${dbToken.value}`
          },
          body: formData
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          dbError.value = data.detail || 'Ошибка создания таблицы';
        } else {
          dbError.value = '';
          // Можно показать уведомление или закрыть модалку
        }
      } catch (e: any) {
        dbError.value = (e as any).message || 'Ошибка';
      } finally {
        dbLoading.value = false;
      }
    }

    const saveSuccessModalVisible = ref(false)

    // --- Сохранение в БД после обучения ---
    const handleSaveToDb = async () => {
      dbLoading.value = true;
      dbError.value = '';
      let schema = selectedDbSchema.value;
      let tableName = '';
      if (!schema) {
        dbError.value = 'Выберите схему.';
        dbLoading.value = false;
        return;
      }
      if (dbSaveMode.value === 'new') {
        tableName = newTableName.value.trim();
        if (!tableName) {
          dbError.value = 'Введите название новой таблицы.';
          dbLoading.value = false;
          return;
        }
        // 1. Создать таблицу
        const formData = new FormData();
        if (!store.selectedFile) {
          dbError.value = 'Файл не выбран.';
          dbLoading.value = false;
          return;
        }
        formData.append('file', store.selectedFile as Blob, store.selectedFile?.name ?? 'uploaded_file');
        formData.append('table_name', tableName);
        formData.append('primary_keys', JSON.stringify(selectedPrimaryKeys.value));
        formData.append('create_table_only', 'true');
        formData.append('db_schema', schema); // <-- исправлено
        const resp = await fetch('http://localhost:8000/create-table-from-file', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${dbToken.value}`
          },
          body: formData
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          dbError.value = data.detail || 'Ошибка создания таблицы';
          dbLoading.value = false;
          return;
        }
      } else {
        tableName = selectedTable.value;
        if (!tableName) {
          dbError.value = 'Не выбрана таблица или не загружен файл';
          dbLoading.value = false;
          return;
        }
        // 2. Проверить структуру
        const formData = new FormData();
        formData.append('file', store.selectedFile as Blob, store.selectedFile?.name ?? 'uploaded_file');
        formData.append('table_name', tableName);
        formData.append('db_schema', schema); // <-- исправлено
        const resp = await fetch('http://localhost:8000/check-df-matches-table-schema', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${dbToken.value}`
          },
          body: formData
        });
        const data = await resp.json();
        if (!data.success) {
          dbError.value = data.detail || 'Структура файла не совпадает с таблицей';
          dbLoading.value = false;
          return;
        }
      }
      // Сохраняем название таблицы в store.uploadDbName
      store.setUploadDbName(tableName);
      // Скрываем модалку автосохранения
      closeAutoSaveModal();
      // Показываем модалку успеха
      saveSuccessModalVisible.value = true;
      setTimeout(() => { saveSuccessModalVisible.value = false; }, 1800);
    }

    // Очищать ошибку при смене radio button
    watch(dbSaveMode, () => {
      dbError.value = ''
    })

    return {
      trainPredictSave,
      canStartTraining,
      startTraining,
      trainingStatus: computed(() => store.trainingStatus),
      isTraining,
      buttonText,
      getStatusMessage,
      showAutoSaveButton,
      canAutoSaveToDb,
      // modal
      autoSaveModalVisible,
      openAutoSaveModal,
      closeAutoSaveModal,
      dbTableNames,
      dbLoading,
      dbError,
      selectedTable,
      newTableName,
      dbSaveMode,
      selectedPrimaryKeys,
      tableData,
      dbTableCountAvailable,
      dbTableCountTotal,
      createTableFromFile,
      saveSuccessModalVisible,
      handleSaveToDb,
      dbSchemas,
      selectedDbSchema,
      dbTablesBySchema,
      filteredDbTables,
      // --- Метрики для разных типов задач ---
      metricOptions: {
        regression: [
          { label: 'MAE (Mean absolute error)', value: 'mae' },
          { label: 'MSE (Mean squared error)', value: 'mse' },
          { label: 'RMSE (Root mean squared error)', value: 'rmse' },
          { label: 'R2 (R squared)', value: 'r2' },
        ],
        binary: [
          { label: 'Accuracy', value: 'accuracy' },
          { label: 'Log loss', value: 'log_loss' },
          { label: 'F1', value: 'f1' },
          { label: 'ROC AUC', value: 'roc_auc_ovr' },
        ],
        multiclass: [
          { label: 'Accuracy', value: 'accuracy' },
          { label: 'Log loss', value: 'log_loss' },
          { label: 'F1 macro', value: 'f1_macro' },
          { label: 'F1 weighted', value: 'f1_weighted' },
          { label: 'Balanced accuracy', value: 'balanced_accuracy' },
        ],
        auto: [
          { label: 'Auto', value: 'auto' },
        ]
      },
    }
  }
})
</script>

<style scoped>
.training {
  margin-top: 2rem;
  /* убираем рамку, фон и паддинг */
  max-width: none;
  padding: 0;
  border: none;
  border-radius: 0;
  background-color: transparent;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
  color: #333;
  text-align: left;
}

.training-checkbox {
  margin-bottom: 20px;
}

.training-status {
  margin-bottom: 20px;
}

.progress-container {
  width: 100%;
  height: 10px;
  background-color: #f3f3f3;
  border-radius: 5px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  background-color: #4caf50;
  transition: width 0.4s ease;
}

.progress-error {
  background-color: #f44336 !important;
}

.status-text {
  margin-top: 5px;
  text-align: center;
}

.error-message {
  color: #f44336;
  margin-top: 10px;
  text-align: center;
}

.train-button {
  width: 100%;
  padding: 10px;
  font-size: 16px;
  color: #fff;
  background-color: #007bff;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.train-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.train-button:not(:disabled):hover {
  background-color: #0056b3;
}

/* Стили для модального окна автосохранения в БД */
.db-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  isolation: isolate;
}
.db-modal {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  min-width: 340px;
  width: 100%;
  min-height: 220px;
  max-height: 90vh;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.close-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.7rem;
  background: none;
  border: none;
  font-size: 2rem;
  color: #888;
  cursor: pointer;
  z-index: 10;
}
.close-btn:active, .close-btn:focus {
  background: none !important;
  outline: none;
  box-shadow: none;
}
.table-preview-loader {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  width: 100%;
}
.table-preview-spinner {
  width: 36px;
  height: 36px;
  border: 4px solid #e3e3e3;
  border-top: 4px solid #2196F3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.upload-to-db-btn {
  width: 100%;
  padding: 0.75rem;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  margin-bottom: 0;
  transition: background-color 0.2s;
}
.upload-to-db-btn:hover {
  background-color: #0d47a1 !important;
}
.error-message {
  color: #f44336;
  margin-top: 10px;
  text-align: center;
}

.db-input,
.db-input-full {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  font-family: inherit;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
}

.connect-btn {
  margin-bottom: 0px;
  width: 100%;
  padding: 0.75rem;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}
.connect-btn:hover {
  background-color: #1976d2;
}

.table-count-info {
  font-size: 0.88rem;
  color: #1976d2;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.db-modal .input-label {
  margin-top: 0;
  font-size: 0.97rem;
  padding: 0;
}

.db-modal .db-input {
  padding: 0.45rem 0.6rem;
  margin-bottom: 0.5rem;
}

.primary-keys-label {
  margin-top: 1.2rem !important;
}

/* Стили для модального окна успешного сохранения */
.success-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  isolation: isolate;
}
.success-modal {
  background: #fff;
  border-radius: 16px;
  padding: 2.5rem 2.5rem 2rem 2.5rem;
  min-width: 340px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(76, 175, 80, 0.18);
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: pop-in 0.18s cubic-bezier(.4,2,.6,1) 1;
}
.success-icon {
  margin-bottom: 1.2rem;
}
.success-text {
  color: #388e3c;
  font-size: 1.25rem;
  font-weight: 600;
  text-align: center;
}
@keyframes pop-in {
  0% { transform: scale(0.7); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
