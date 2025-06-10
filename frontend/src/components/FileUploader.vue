<template>
  <div class="file-uploader">
    <h3 class="section-title">Настройка обучения</h3>

    <!-- Данные для обучения (accordion) -->
    <div class="accordion-section">
      <button class="accordion-toggle train-toggle" @click="onTrainAccordionClick">
        <span>{{ trainOpen ? '▼' : '►' }}</span>
        Загрузка данных для обучения
      </button>
      <transition name="accordion-fade">
        <div v-show="trainOpen" class="accordion-content">
          <div class="upload-section">
            <h4 class="subsection-title">Загрузка данных для обучения</h4>
            <div class="upload-zone" @dragover.prevent @drop.prevent="handleDrop">
              <input 
                type="file" 
                ref="fileInput"
                accept=".csv,.xlsx,.xls"
                @change="handleFileChange"
                style="display: none"
              >
              <button @click="fileInput && fileInput.click()" class="choose-file-btn">
                📂 Выбрать файл
              </button>
              <p>или перетащите файл сюда</p>
            </div>
            <div v-if="selectedFile" class="file-info">
              Выбран файл: {{ selectedFile.name }}
            </div>
            <button 
              @click="handleUpload" 
              class="upload-button" 
              :disabled="!selectedFile"
            >
              <span v-if="isLoading" class="spinner-wrap">
                <span class="spinner"></span>Загрузка...
              </span>
              <span v-else>📂 Загрузить данные из файла</span>
            </button>
            <h4 v-if="dbConnected" class="subsection-title">Работа с базой данных</h4>
            <button
              v-if="dbConnected"
              class="db-load-btn"
              @click="openDbModal"
              style="margin-top: 0.5rem; background: #388e3c;"
            >
              🗄️ Загрузить данные из БД
            </button>
            <button
              v-if="dbConnected && fileLoaded"
              class="upload-to-db-btn"
              @click="openUploadToDbModal"
              :disabled="isLoading"
              style="margin-top: 0.5rem;"
            >
              ⬆️ Загрузить данные в БД
            </button>
            <button
              v-if="dbConnected && fileLoaded"
              class="download-from-app-btn"
              :disabled="!dbConnected"
              @click="downloadFromApp"
              style="width: 100%; margin-top: 0.5rem; margin-bottom: 10px;"
            >
              ⬇️ Скачать данные для обучения из приложения
            </button>
          </div>
        </div>
      </transition>
    </div>

    <!-- Данные для прогноза (accordion) -->
    <div class="accordion-section">
      <button class="accordion-toggle test-toggle" @click="onTestAccordionClick">
        <span>{{ testOpen ? '▼' : '►' }}</span>
        Загрузка данных для прогноза
      </button>
      <transition name="accordion-fade">
        <div v-show="testOpen" class="accordion-content">
          <div class="upload-section">
            <h4 class="subsection-title">Загрузка данных для прогноза</h4>
            <div class="upload-zone" @dragover.prevent @drop.prevent="handleTestDrop">
              <input 
                type="file" 
                ref="testFileInput"
                accept=".csv,.xlsx,.xls"
                @change="handleTestFileChange"
                style="display: none"
              >
              <button @click="testFileInput && testFileInput.click()" class="choose-file-btn">
                📂 Выбрать файл
              </button>
              <p>или перетащите файл сюда</p>
            </div>
            <div v-if="selectedTestFile" class="file-info">
              Выбран файл: {{ selectedTestFile.name }}
            </div>
            <button 
              @click="handleTestUpload" 
              class="upload-button" 
              :disabled="!selectedTestFile"
            >
              <span v-if="isTestLoading" class="spinner-wrap">
                <span class="spinner"></span>Загрузка...
              </span>
              <span v-else>📂 Загрузить данные из файла</span>
            </button>
            <h4 v-if="dbConnected" class="subsection-title">Работа с базой данных</h4>
            <button
              v-if="dbConnected"
              class="db-load-btn"
              @click="openTestDbModal"
              style="margin-top: 0.5rem; background: #388e3c;"
            >
              🗄️ Загрузить данные из БД
            </button>
            <button
              v-if="dbConnected && testFileLoaded"
              class="upload-to-db-btn"
              @click="openTestUploadToDbModal"
              :disabled="isTestLoading"
              style="margin-top: 0.5rem;"
            >
              ⬆️ Загрузить данные в БД
            </button>
            <button
              v-if="dbConnected && testFileLoaded"
              class="download-from-app-btn"
              :disabled="!dbConnected"
              @click="downloadTestFromApp"
              style="width: 100%; margin-top: 0.5rem; margin-bottom: 10px;"
            >
              ⬇️ Скачать данные для прогноза из приложения
            </button>
          </div>
        </div>
      </transition>
    </div>

    <!-- Модальное окно выбора таблицы из БД -->
    <Teleport to="body">
      <div v-if="dbModalVisible" class="db-modal-overlay" @click="closeDbModal">
        <div class="db-modal" @click.stop>
          <button class="close-btn" @click="closeDbModal">×</button>
          <h3 class="section-title" style="margin-bottom:1.5rem; border-bottom: none; font-size: 1.3rem;">Выбор таблицы</h3>
          <div class="db-modal-table-area">
            <div v-if="dbTablesLoading" style="color:#888;">Загрузка таблиц...</div>
            <div v-else-if="Object.values(dbTablesBySchema).flat().length === 0" style="color:#f44336;">Нет доступных таблиц</div>
            <div v-else class="db-modal-content">
              <!-- УДАЛЕНО: доступно таблиц -->
              <!-- Выбор схемы -->
              <div>
                <label class="input-label" style="display:block; margin-bottom:0.5rem;">
                  Выберите схему:
                </label>
                <select v-model="selectedDbSchema" class="db-input" style="width:100%;margin-bottom:0.5rem;">
                  <option v-for="schema in dbSchemas" :key="schema" :value="schema">{{ schema }}</option>
                </select>
              </div>
              <!-- Выбор таблицы -->
              <label class="input-label" style="display:block; margin-bottom:0.5rem;">Выберите таблицу:</label>
              <div v-if="dbTableCountAvailable !== null && dbTableCountTotal !== null" class="table-count-info">
                Доступно {{ dbTableCountAvailable }} таблиц из {{ dbTableCountTotal }}
              </div>
              <select v-model="selectedDbTable" class="db-input db-input-full">
                <option value="" disabled selected>Выберите таблицу...</option>
                <option v-for="table in filteredDbTables" :key="table" :value="table">{{ table }}</option>
              </select>
              
              <div class="table-preview-fixed">
                <div v-if="tablePreviewLoading" class="table-preview-loader">
                  <span class="table-preview-spinner"></span>
                </div>
                <div v-else-if="tablePreviewError" class="error-message" style="display:flex;align-items:center;justify-content:center;height:100%;">{{ tablePreviewError }}</div>
                <div v-else-if="tablePreview && tablePreview.length" class="table-preview-scroll">
                  <table style="width:100%; border-collapse:collapse; font-size:0.95rem;">
                    <thead>
                      <tr>
                        <th v-for="key in Object.keys(tablePreview[0])" :key="key" style="border-bottom:1px solid #e0e0e0; padding:0.3rem 0.5rem; background:#f5f5f5;">{{ key }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in tablePreview" :key="idx">
                        <td v-for="key in Object.keys(tablePreview[0])" :key="key" style="padding:0.3rem 0.5rem; border-bottom:1px solid #f0f0f0;">{{ row[key] }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else id="table-preview-placeholder" class="table-preview-placeholder">Выберите таблицу для предпросмотра</div>
              </div>
            </div>
          </div>
          <div class="db-modal-footer">
            <button class="connect-btn" style="width:100%;" :disabled="!selectedDbTable || isLoadingFromDb" @click="loadTableFromDb">
              <span v-if="isLoadingFromDb" class="spinner-wrap"><span class="spinner"></span>Загрузка...</span>
              <span v-else>Загрузить таблицу</span>
            </button>
            <div v-if="dbError" class="error-message">{{ dbError }}</div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно выбора таблицы из БД для данных для прогноза -->
    <Teleport to="body">
      <div v-if="testDbModalVisible" class="db-modal-overlay" @click="closeTestDbModal">
        <div class="db-modal" @click.stop>
          <button class="close-btn" @click="closeTestDbModal">×</button>
          <h3 class="section-title" style="margin-bottom:1.5rem; border-bottom: none; font-size: 1.3rem;">Выбор таблицы (Данные для прогноза)</h3>
          <div class="db-modal-table-area">
            <div v-if="testDbTablesLoading" style="color:#888;">Загрузка таблиц...</div>
            <div v-else-if="Object.values(testDbTablesBySchema).flat().length === 0" style="color:#f44336;">Нет доступных таблиц</div>
            <div v-else class="db-modal-content">
              <div>
                <label class="input-label" style="display:block; margin-bottom:0.5rem;">
                  Выберите схему:
                </label>
                <select v-model="testSelectedDbSchema" class="db-input" style="width:100%;margin-bottom:0.5rem;">
                  <option v-for="schema in testDbSchemas" :key="schema" :value="schema">{{ schema }}</option>
                </select>
              </div>
              <label class="input-label" style="display:block; margin-bottom:0.5rem;">Выберите таблицу:</label>
              <div v-if="testDbTableCountAvailable !== null && testDbTableCountTotal !== null" class="table-count-info">
                Доступно {{ testDbTableCountAvailable }} таблиц из {{ testDbTableCountTotal }}
              </div>
              <select v-model="testSelectedDbTable" class="db-input db-input-full">
                <option value="" disabled selected>Выберите таблицу...</option>
                <option v-for="table in filteredTestDbTables" :key="table" :value="table">{{ table }}</option>
              </select>
              <div class="table-preview-fixed">
                <div v-if="testTablePreviewLoading" class="table-preview-loader">
                  <span class="table-preview-spinner"></span>
                </div>
                <div v-else-if="testTablePreviewError" class="error-message" style="display:flex;align-items:center;justify-content:center;height:100%;">{{ testTablePreviewError }}</div>
                <div v-else-if="testTablePreview && testTablePreview.length" class="table-preview-scroll">
                  <table style="width:100%; border-collapse:collapse; font-size:0.95rem;">
                    <thead>
                      <tr>
                        <th v-for="key in Object.keys(testTablePreview[0])" :key="key" style="border-bottom:1px solid #e0e0e0; padding:0.3rem 0.5rem; background:#f5f5f5;">{{ key }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in testTablePreview" :key="idx">
                        <td v-for="key in Object.keys(testTablePreview[0])" :key="key" style="padding:0.3rem 0.5rem; border-bottom:1px solid #f0f0f0;">{{ row[key] }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else id="test-table-preview-placeholder" class="table-preview-placeholder">Выберите таблицу для предпросмотра</div>
              </div>
            </div>
          </div>
          <div class="db-modal-footer">
            <button class="connect-btn" style="width:100%;" :disabled="!testSelectedDbTable || isTestLoadingFromDb" @click="loadTestTableFromDb">
              <span v-if="isTestLoadingFromDb" class="spinner-wrap"><span class="spinner"></span>Загрузка...</span>
              <span v-else>Загрузить таблицу</span>
            </button>
            <div v-if="testDbError" class="error-message">{{ testDbError }}</div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно для загрузки файла в БД -->
    <Teleport to="body">
      <div v-if="uploadToDbModalVisible" class="db-modal-overlay" @click="closeUploadToDbModal">
        <div class="db-modal upload-to-db-modal" id="upload-to-db-modal" @click.stop>
          <button class="close-btn" @click="closeUploadToDbModal">×</button>
          <h3 style="margin-bottom:1rem">Загрузка файла в БД</h3>
          <!-- Выбор режима: новая таблица или существующая -->
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
              <select v-model="selectedUploadDbSchema" class="db-input">
                <option v-for="schema in uploadDbSchemas" :key="schema" :value="schema">{{ schema }}</option>
              </select>
            </div>
            <!-- Заголовок и поле для названия таблицы -->
            <div style="margin-top:0.7rem;">
              <label class="input-label">Название таблицы:</label>
              <input v-model="uploadTableName" class="db-input db-input-full" placeholder="Введите название таблицы" />
            </div>
            <div v-if="tableData && tableData.length" style="margin-bottom:1rem;">
              <label style="font-weight:500; color:#333; margin-bottom:0.5rem; display:block; margin-top:1.2rem;">Выберите первичные ключи (опционально):</label>
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
              <select v-model="selectedUploadDbSchema" class="db-input" style="width:100%;margin-bottom:1rem;">
                <option v-for="schema in uploadDbSchemas" :key="schema" :value="schema">{{ schema }}</option>
              </select>
            </div>
            <label class="input-label" style="display:block; margin-bottom:0.5rem;">Выберите таблицу:</label>
            <div v-if="dbTableCountAvailable !== null && dbTableCountTotal !== null" class="table-count-info">
              Доступно {{ dbTableCountAvailable }} таблиц из {{ dbTableCountTotal }}
            </div>
            <select v-model="uploadTableName" class="db-input db-input-full" style="margin-bottom:1rem;">
              <option value="" disabled selected>Загрузка списка...</option>
              <option v-for="table in filteredUploadDbTables" :key="table" :value="table">{{ table }}</option>
            </select>
          </div>

          <div class="upload-to-db-footer">
            <button class="upload-to-db-btn" :disabled="!uploadTableName || uploadToDbLoading" @click="uploadFileToDb">
              <span v-if="uploadToDbLoading" class="spinner-wrap"><span class="spinner"></span>Загрузка...</span>
              <span v-else>Загрузить в БД</span>
            </button>
            <div v-if="uploadToDbError" class="error-message upload-to-db-error-area">{{ uploadToDbError }}</div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно успешной загрузки файла в БД (данные для обучения) -->
    <Teleport to="body">
      <div v-if="uploadSuccessModalVisible" class="success-modal-overlay">
        <div class="success-modal">
          <div class="success-icon">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#4CAF50"/>
              <path d="M24 42L36 54L56 34" stroke="white" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="success-text">Данные успешно загружены в БД</div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно успешной загрузки данных из БД (данные для обучения) -->
    <Teleport to="body">
      <div v-if="downloadSuccessModalVisible" class="success-modal-overlay">
        <div class="success-modal">
          <div class="success-icon">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#4CAF50"/>
              <path d="M24 42L36 54L56 34" stroke="white" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="success-text">Данные успешно загружены <b>из БД</b></div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно успешной загрузки файла в БД (данные для прогноза) -->
    <Teleport to="body">
      <div v-if="testUploadSuccessModalVisible" class="success-modal-overlay">
        <div class="success-modal">
          <div class="success-icon">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#4CAF50"/>
              <path d="M24 42L36 54L56 34" stroke="white" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="success-text">Данные для прогноза успешно загружены <b>в БД</b></div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно успешной загрузки данных для прогноза из БД -->
    <Teleport to="body">
      <div v-if="testDownloadSuccessModalVisible" class="success-modal-overlay">
        <div class="success-modal">
          <div class="success-icon">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#4CAF50"/>
              <path d="M24 42L36 54L56 34" stroke="white" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="success-text">Данные для прогноза успешно загружены <b>из БД</b></div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно для загрузки файла в БД (данные для прогноза) -->
    <Teleport to="body">
      <div v-if="testUploadToDbModalVisible" class="db-modal-overlay" @click="closeTestUploadToDbModal">
        <div class="db-modal upload-to-db-modal" id="test-upload-to-db-modal" @click.stop>
          <button class="close-btn" @click="closeTestUploadToDbModal">×</button>
          <h3 style="margin-bottom:1rem">Загрузка файла для прогноза в БД</h3>
          <!-- Выбор режима: новая таблица или существующая -->
          <div style="margin-bottom:1rem; display:flex; gap:1.5rem; align-items:center;">
            <label style="display:flex; align-items:center; gap:6px; font-weight:500;">
              <input type="radio" value="new" v-model="testDbSaveMode" />
              Создать новую таблицу
            </label>
            <label style="display:flex; align-items:center; gap:6px; font-weight:500;">
              <input type="radio" value="existing" v-model="testDbSaveMode" />
              Загрузить в существующую
            </label>
          </div>
          <!-- Новая таблица -->
          <div v-if="testDbSaveMode === 'new'">
            <div>
              <label class="input-label">Выберите схему:</label>
              <select v-model="testSelectedUploadDbSchema" class="db-input">
                <option v-for="schema in testUploadDbSchemas" :key="schema" :value="schema">{{ schema }}</option>
              </select>
            </div>
            <div style="margin-top:0.7rem;">
              <label class="input-label">Название таблицы:</label>
              <input v-model="testUploadTableName" class="db-input db-input-full" placeholder="Введите название таблицы" />
            </div>
            <div v-if="store.testTableData && store.testTableData.length" style="margin-bottom:1rem;">
              <label style="font-weight:500; color:#333; margin-bottom:0.5rem; display:block; margin-top:1.2rem;">Выберите первичные ключи (опционально):</label>
              <div style="display:flex; flex-wrap:wrap; gap:8px;">
                <label v-for="col in Object.keys(store.testTableData[0])" :key="col" style="display:flex; align-items:center; gap:4px;">
                  <input type="checkbox" :value="col" v-model="testSelectedPrimaryKeys" />
                  <span>{{ col }}</span>
                </label>
              </div>
            </div>
          </div>
          <!-- Существующая таблица -->
          <div v-if="testDbSaveMode === 'existing'">
            <div style="margin-bottom: 1rem;">
              <label class="input-label" style="display:block; margin-bottom:0.5rem;">
                Выберите схему:
              </label>
              <select v-model="testSelectedUploadDbSchema" class="db-input" style="width:100%;margin-bottom:1rem;">
                <option v-for="schema in testUploadDbSchemas" :key="schema" :value="schema">{{ schema }}</option>
              </select>
            </div>
            <label class="input-label" style="display:block; margin-bottom:0.5rem;">Выберите таблицу:</label>
            <div v-if="testDbTableCountAvailable !== null && testDbTableCountTotal !== null" class="table-count-info">
              Доступно {{ testDbTableCountAvailable }} таблиц из {{ testDbTableCountTotal }}
            </div>
            <select v-model="testUploadTableName" class="db-input db-input-full" style="margin-bottom:1rem;">
              <option value="" disabled selected>Загрузка списка...</option>
              <option v-for="table in filteredTestUploadDbTables" :key="table" :value="table">{{ table }}</option>
            </select>
          </div>
          <div class="upload-to-db-footer">
            <button class="upload-to-db-btn" :disabled="!testUploadTableName || testUploadToDbLoading" @click="uploadTestFileToDb">
              <span v-if="testUploadToDbLoading" class="spinner-wrap"><span class="spinner"></span>Загрузка...</span>
              <span v-else>Загрузить в БД</span>
            </button>
            <div v-if="testUploadToDbError" class="error-message upload-to-db-error-area">{{ testUploadToDbError }}</div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue'
import { useMainStore } from '../stores/mainStore'
import * as XLSX from 'xlsx'

export default defineComponent({
  name: 'FileUploader',
  emits: ['file-loaded'],

  setup(props, { emit }) {
    const store = useMainStore()
    const fileInput = ref<HTMLInputElement | null>(null)
    const selectedFile = ref<File | null>(null)
    const isLoading = ref(false)
    const fileLoaded = ref(false)
    // --- TEST DATA STATE ---
    const testFileInput = ref<HTMLInputElement | null>(null)
    const selectedTestFile = ref<File | null>(null)
    const isTestLoading = ref(false)
    const testFileLoaded = ref(false)
    // --- DB upload modal state ---
    const dbModalVisible = ref(false)
    const dbTablesLoading = ref(false) // <--- add loading state
    const selectedDbTable = ref('')
    const isLoadingFromDb = ref(false)
    const dbError = ref('')
    const tablePreview = ref<any[] | null>(null)
    const tablePreviewLoading = ref(false)
    const tablePreviewError = ref('')
    // --- Upload to DB modal state ---
    const uploadToDbModalVisible = ref(false)
    const uploadTableName = ref('')
    const uploadToDbLoading = ref(false)
    const uploadToDbError = ref('')
    const uploadSuccessModalVisible = ref(false)
    const downloadSuccessModalVisible = ref(false) // <--- новое состояние для успешной загрузки из БД
    const selectedPrimaryKeys = ref<string[]>([]) // <--- новое состояние для выбранных первичных ключей
    const dbSaveMode = ref<'new' | 'existing'>('new') // <--- состояние для режима сохранения в БД
    const tableData = computed(() => store.tableData)
    const uploadDbTables = ref<string[]>([])
    const uploadDbTablesLoading = ref(false)
    const dbTableCountAvailable = ref<number | null>(null)
    const dbTableCountTotal = ref<number | null>(null)
    // --- DB schemas state ---
    const dbSchemas = ref<string[]>([])
    const dbTablesBySchema = ref<{[schema: string]: string[]}>({})
    const selectedDbSchema = ref('')
    const filteredDbTables = computed(() => {
      if (!selectedDbSchema.value) return []
      return dbTablesBySchema.value[selectedDbSchema.value] || []
    })
    // --- Upload to DB schemas state (добавлено) ---
    const uploadDbSchemas = ref<string[]>([])
    const uploadDbTablesBySchema = ref<{[schema: string]: string[]}>({})
    const selectedUploadDbSchema = ref('')
    const filteredUploadDbTables = computed(() => {
      const schema = selectedUploadDbSchema.value;
      return schema && uploadDbTablesBySchema.value[schema]
        ? uploadDbTablesBySchema.value[schema]
        : [];
    })
    // --- TEST DB MODALS ---
    const testDbModalVisible = ref(false)
    const testSelectedDbTable = ref('')
    const isTestLoadingFromDb = ref(false)
    const testDbError = ref('')
    const testTablePreview = ref<any[] | null>(null)
    const testTablePreviewLoading = ref(false)
    const testTablePreviewError = ref('')
    const testDbTablesLoading = ref(false)
    // --- Upload to DB modal state for test ---
    const testUploadToDbModalVisible = ref(false)
    const testUploadTableName = ref('')
    const testUploadToDbLoading = ref(false)
    const testUploadToDbError = ref('')
    const testUploadSuccessModalVisible = ref(false)
    const testDownloadSuccessModalVisible = ref(false) // <--- новое состояние для успешной загрузки из БД (тестовые)
    const testSelectedPrimaryKeys = ref<string[]>([])
    const testDbSaveMode = ref<'new' | 'existing'>('new')
    const testUploadDbTables = ref<string[]>([])
    const testUploadDbTablesLoading = ref(false)
    const testUploadDbSchemas = ref<string[]>([])
    const testSelectedUploadDbSchema = ref('')
    const testUploadDbTablesBySchema = ref<{[schema: string]: string[]}>({})
    const filteredTestUploadDbTables = computed(() => {
      const schema = testSelectedUploadDbSchema.value;
      return schema && testUploadDbTablesBySchema.value[schema]
        ? testUploadDbTablesBySchema.value[schema]
        : [];
    })
    const testDbTableCountAvailable = ref<number | null>(null)
    const testDbTableCountTotal = ref<number | null>(null)
    // --- DB schemas state for test ---
    const testDbSchemas = ref<string[]>([])
    const testDbTablesBySchema = ref<{[schema: string]: string[]}>({})
    const testSelectedDbSchema = ref('')
    const filteredTestDbTables = computed(() => {
      if (!testSelectedDbSchema.value) return []
      return testDbTablesBySchema.value[testSelectedDbSchema.value] || []
    })

    // Accordion state for upload sections
    const trainOpen = ref(false)
    const testOpen = ref(false)

    // --- Получение таблиц и схем из БД ---
    async function fetchDbTables() {
      dbTablesLoading.value = true
      try {
        const response = await fetch('http://localhost:8000/get-tables', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
        })
        const result = await response.json()
        if (result.success) {
          dbSchemas.value = Object.keys(result.tables)
          dbTablesBySchema.value = result.tables
          selectedDbSchema.value = dbSchemas.value[0] || ''
          dbTableCountAvailable.value = result.count_available ?? 0
          dbTableCountTotal.value = result.count_total ?? 0
        } else {
          dbSchemas.value = []
          dbTablesBySchema.value = {}
          selectedDbTable.value = ''
          dbTableCountAvailable.value = null
          dbTableCountTotal.value = null
        }
      } catch (e) {
        dbSchemas.value = []
        dbTablesBySchema.value = {}
        selectedDbTable.value = ''
        dbTableCountAvailable.value = null
        dbTableCountTotal.value = null
      } finally {
        dbTablesLoading.value = false
      }
    }

    // Для шаблона
    const dbConnected = computed(() => store.dbConnected)

    const chunkSize = computed({
      get: () => store.chunkSize,
      set: (value: number) => store.setChunkSize(value)
    })

    // Преобразование Excel serial date в строку (YYYY-MM-DD или с временем)
    function convertExcelDates(
      data: any[],
      xlsxModule?: typeof import('xlsx')
    ): any[] {
      if (!Array.isArray(data) || data.length === 0) return data;
      // Найти все колонки, которые могут быть датой
      const dateLikeColumns = Object.keys(data[0]).filter(
        key => key.toLowerCase().includes('date') || key.toLowerCase().includes('timestamp')
      );
      if (dateLikeColumns.length === 0) return data;
      // Попробовать преобразовать только если значение - число и похоже на Excel serial
      return data.map(row => {
        const newRow = { ...row };
        dateLikeColumns.forEach(col => {
          const value = row[col];
          if (
            typeof value === 'number' &&
            value > 20000 && value < 90000 &&
            xlsxModule &&
            (xlsxModule as any).SSF &&
            typeof (xlsxModule as any).SSF.parse_date_code === 'function'
          ) {
            const dateObj = (xlsxModule as any).SSF.parse_date_code(value);
            if (dateObj) {
              const pad = (n: number) => n.toString().padStart(2, '0');
              // Если есть время и оно не полуночь, добавлять только часы (без минут и секунд)
              let str = `${dateObj.y}-${pad(dateObj.m)}-${pad(dateObj.d)}`;
              if (
                dateObj.H !== undefined &&
                (dateObj.H !== 0 || dateObj.M !== 0 || dateObj.S !== 0)
              ) {
                str += ` ${pad(dateObj.H)}`;
              }
              newRow[col] = str;
            }
          }
        });
        return newRow;
      });
    }

    const processFile = async (file: File) => {
      try {
        store.setFile(file)
        // Используем Web Worker для Excel
        if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
          await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
              // Используем Vite worker с импортом из node_modules
              const worker = new Worker(new URL('../worker-xlsx.ts', import.meta.url), { type: 'module' });
              worker.onmessage = function(event) {
                if (event.data.success) {
                  import('xlsx').then(XLSX => {
                    const converted = convertExcelDates(event.data.data, XLSX);
                    store.setTableData(converted)
                    emit('file-loaded', converted)
                    resolve(null)
                  });
                } else {
                  reject(event.data.error)
                }
                worker.terminate();
              };
              worker.postMessage({
                fileData: e.target?.result ?? '',
                fileName: file.name,
                maxRows: 1000000
              });
            };
            reader.onerror = (err) => reject(err);
            reader.readAsBinaryString(file);
          });
        } else {
          const data = await readFileData(file)
          // Преобразуем даты после получения данных
          const XLSX = await import('xlsx');
          const converted = convertExcelDates(data, XLSX);
          store.setTableData(converted)
          emit('file-loaded', converted)
        }
      } catch (error) {
        // Ошибка обработки файла
      }
    }

    const readFileData = (file: File): Promise<any[]> => {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        
        reader.onload = (e) => {
          try {
            const data = e.target?.result ?? ''
            const workbook = XLSX.read(data, { type: 'binary' })
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
            const jsonData = XLSX.utils.sheet_to_json(firstSheet)
            resolve(jsonData)
          } catch (error) {
            reject(error)
          }
        }
        
        reader.onerror = (error) => reject(error)
        reader.readAsBinaryString(file)
      })
    }

    const handleFileChange = (event: Event) => {
      const target = event.target as HTMLInputElement
      const file = target.files?.[0]
      if (file) {
        selectedFile.value = file
        store.setFile(file) // Сохраняем файл в хранилище
        fileLoaded.value = false // сброс при выборе нового файла
      }
    }

    const handleDrop = (event: DragEvent) => {
      const file = event.dataTransfer?.files[0]
      if (file) {
        selectedFile.value = file
        store.setFile(file) // Сохраняем файл в хранилище
        fileLoaded.value = false // сброс при выборе нового файла
      }
    }

    const handleUpload = async () => {
      if (!selectedFile.value) return
      isLoading.value = true
      try {
        store.setFile(selectedFile.value) // Убедимся, что файл сохранен в хранилище перед загрузкой
        await processFile(selectedFile.value)
        fileLoaded.value = true // только после успешной загрузки
        store.setFileLoaded(true) // <-- теперь и в store
      } finally {
        isLoading.value = false
      }
    }

    const openDbModal = async () => {
      dbModalVisible.value = true
      dbError.value = ''
      selectedDbTable.value = ''
      selectedDbSchema.value = ''
      if (store.dbConnected && store.authToken) {
        dbTablesLoading.value = true
        try {
          const response = await fetch('http://localhost:8000/get-tables', {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${store.authToken}`
            },
          });
          const result = await response.json();
          if (result.success) {
            dbSchemas.value = Object.keys(result.tables)
            dbTablesBySchema.value = result.tables
            selectedDbSchema.value = dbSchemas.value[0] || ''
            dbTableCountAvailable.value = result.count_available ?? 0
            dbTableCountTotal.value = result.count_total ?? 0
            dbError.value = ''
          } else {
            dbSchemas.value = []
            dbTablesBySchema.value = {}
            selectedDbTable.value = ''
            dbTableCountAvailable.value = null
            dbTableCountTotal.value = null
          }
        } catch (e: any) {
          dbError.value = 'Ошибка при загрузке таблиц: ' + (e && typeof e === 'object' && 'message' in e ? (e as any).message : String(e));
          dbSchemas.value = []
          dbTablesBySchema.value = {}
          selectedDbTable.value = ''
          dbTableCountAvailable.value = null
          dbTableCountTotal.value = null
        } finally {
          dbTablesLoading.value = false
        }
      }
    }
    function closeDbModal() {
      dbModalVisible.value = false
      dbError.value = ''
    }

    async function loadTableFromDb() {
      if (!selectedDbTable.value || !selectedDbSchema.value) return
      dbError.value = ''
      isLoadingFromDb.value = true
      try {
        const response = await fetch('http://localhost:8000/download-table-from-db', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
          body: JSON.stringify({ db_schema: selectedDbSchema.value, table: selectedDbTable.value })
        })
        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          dbError.value = err.detail || 'Ошибка загрузки файла из БД.'
          return
        }
        // Получаем blob Excel-файла
        const blob = await response.blob()
        // --- FIX: Always use .xlsx extension for DB download ---
        const file = new File([blob], `${selectedDbTable.value}.xlsx`, { type: blob.type })
        selectedFile.value = file
        store.setFile(file)
        // Обрабатываем файл как обычную загрузку (Excel)
        await processFile(file)
        fileLoaded.value = true
        store.setFileLoaded(true) // <--- добавлено для синхронизации состояния
        emit('file-loaded', store.tableData)
        closeDbModal()
        downloadSuccessModalVisible.value = true
        setTimeout(() => { downloadSuccessModalVisible.value = false }, 1800)
      } catch (error) {
        dbError.value = 'Ошибка загрузки данных из БД: ' + (error && typeof error === 'object' && 'message' in error ? error.message : String(error))
      } finally {
        isLoadingFromDb.value = false
      }
    }

    async function fetchTablePreview(tableName: string) {
      if (!tableName || !selectedDbSchema.value) {
        tablePreview.value = null
        return
      }
      tablePreviewLoading.value = true
      tablePreviewError.value = ''
      try {
        const response = await fetch('http://localhost:8000/get-table-preview', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
          body: JSON.stringify({ db_schema: selectedDbSchema.value, table: tableName })
        })
        const result = await response.json()
        if (result.success && Array.isArray(result.data)) {
          tablePreview.value = result.data
        } else {
          tablePreview.value = null
          tablePreviewError.value = result.detail || 'Не удалось получить предпросмотр.'
        }
      } catch (e: any) {
        tablePreview.value = null
        tablePreviewError.value = 'Ошибка предпросмотра: ' + (e?.message || e)
      } finally {
        tablePreviewLoading.value = false
      }
    }

    // Следим за изменением выбранной таблицы
    watch(selectedDbTable, (val) => {
      if (val) fetchTablePreview(val)
      else tablePreview.value = null
    })

    // Добавляем обработчик для загрузки файла в БД
    async function uploadFileToDb() {
      if (!selectedFile.value || !uploadTableName.value || !selectedUploadDbSchema.value) return
      uploadToDbLoading.value = true
      uploadToDbError.value = ''
      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('db_schema', selectedUploadDbSchema.value) // <-- исправлено: schema -> db_schema
        formData.append('table_name', uploadTableName.value)
        formData.append('primary_keys', JSON.stringify(selectedPrimaryKeys.value))
        formData.append('dbSaveMode', dbSaveMode.value)
        const response = await fetch('http://localhost:8000/upload-excel-to-db', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${store.authToken}`
          },
          body: formData
        })
        const result = await response.json()
        if (result.success) {
          closeUploadToDbModal()
          uploadSuccessModalVisible.value = true
          setTimeout(() => { uploadSuccessModalVisible.value = false }, 1800)
        } else {
          uploadToDbError.value = result.detail || 'Ошибка при загрузке файла в БД.'
        }
      } catch (e: any) {
        uploadToDbError.value = 'Ошибка: ' + (e?.message || e)
      } finally {
        uploadToDbLoading.value = false
      }
    }

    const openUploadToDbModal = () => {
      uploadToDbModalVisible.value = true
      uploadTableName.value = ''
      uploadToDbError.value = ''
      selectedPrimaryKeys.value = []
      dbSaveMode.value = 'new'
      selectedUploadDbSchema.value = ''
      if (store.dbConnected && store.authToken) {
        uploadDbTablesLoading.value = true
        fetch('http://localhost:8000/get-tables', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
        })
          .then(res => res.json())
          .then(result => {
            if (result.success) {
              uploadDbSchemas.value = Object.keys(result.tables)
              uploadDbTablesBySchema.value = result.tables
              selectedUploadDbSchema.value = uploadDbSchemas.value[0] || ''
              uploadTableName.value = ''
              dbTableCountAvailable.value = result.count_available ?? 0
              dbTableCountTotal.value = result.count_total ?? 0
            } else {
              uploadDbSchemas.value = []
              uploadDbTablesBySchema.value = {}
              uploadTableName.value = ''
              dbTableCountAvailable.value = null
              dbTableCountTotal.value = null
            }
          })
          .catch(() => {
            uploadDbSchemas.value = []
            uploadDbTablesBySchema.value = {}
            uploadTableName.value = ''
            dbTableCountAvailable.value = null
            dbTableCountTotal.value = null
          })
          .finally(() => { uploadDbTablesLoading.value = false })
      } else {
        uploadDbSchemas.value = []
        uploadDbTablesBySchema.value = {}
        uploadTableName.value = ''
        dbTableCountAvailable.value = null
        dbTableCountTotal.value = null
      }
    }
    function closeUploadToDbModal() {
      uploadToDbModalVisible.value = false
      uploadTableName.value = ''
      uploadToDbError.value = ''
      selectedPrimaryKeys.value = [] // Сбрасываем выбранные первичные ключи при закрытии модального окна
    }

    // Скачать файл, который был загружен вручную или получен из БД
    const downloadFromApp = () => {
      if (!selectedFile.value) {
        alert('Нет файла для скачивания. Сначала загрузите файл вручную или из БД.');
        return;
      }
      const file = selectedFile.value;
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(file);
      link.download = file.name || 'downloaded_file.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    // --- TEST DATA LOGIC ---
    const handleTestFileChange = (event: Event) => {
      const target = event.target as HTMLInputElement
      const file = target.files?.[0]
      if (file) {
        selectedTestFile.value = file
        store.setSelectedTestFile(file) // Сохраняем тестовый файл в хранилище
        testFileLoaded.value = false
      }
    }
    const handleTestDrop = (event: DragEvent) => {
      const file = event.dataTransfer?.files[0]
      if (file) {
        selectedTestFile.value = file
        store.setSelectedTestFile(file) // Сохраняем тестовый файл в хранилище
        testFileLoaded.value = false
      }
    }
    const processTestFile = async (file: File) => {
      try {
        // Аналогично processFile, но для тестовых данных
        if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
          await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
              const worker = new Worker(new URL('../worker-xlsx.ts', import.meta.url), { type: 'module' });
              worker.onmessage = function(event) {
                if (event.data.success) {
                  import('xlsx').then(XLSX => {
                    const converted = convertExcelDates(event.data.data, XLSX);
                    store.setTestTableData(converted)
                    resolve(null)
                  });
                } else {
                  reject(event.data.error)
                }
                worker.terminate();
              };
              worker.postMessage({
                fileData: e.target?.result ?? '',
                fileName: file.name,
                maxRows: 1000000
              });
            };
            reader.onerror = (err) => reject(err);
            reader.readAsBinaryString(file);
          });
        } else {
          const data = await readFileData(file)
          const XLSX = await import('xlsx');
          const converted = convertExcelDates(data, XLSX);
          store.setTestTableData(converted)
        }
      } catch (error) {
        // Ошибка обработки тестового файла
      }
    }
    const handleTestUpload = async () => {
      if (!selectedTestFile.value) return
      isTestLoading.value = true
      try {
        await processTestFile(selectedTestFile.value)
        testFileLoaded.value = true
        store.setSelectedTestFile(selectedTestFile.value) // Убедимся, что тестовый файл сохранен после загрузки
        store.setTestFileLoaded(true) // <-- теперь и в store
      } finally {
        isTestLoading.value = false
      }
    }
    // --- TEST DB MODAL LOGIC ---
    const openTestDbModal = async () => {
      testDbModalVisible.value = true
      testDbError.value = ''
      testSelectedDbTable.value = ''
      testSelectedDbSchema.value = ''
      if (store.dbConnected && store.authToken) {
        testDbTablesLoading.value = true
        try {
          const response = await fetch('http://localhost:8000/get-tables', {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${store.authToken}`
            },
          });
          const result = await response.json();
          if (result.success) {
            testDbSchemas.value = Object.keys(result.tables)
            testDbTablesBySchema.value = result.tables
            testSelectedDbSchema.value = testDbSchemas.value[0] || ''
            testDbTableCountAvailable.value = result.count_available ?? 0
            testDbTableCountTotal.value = result.count_total ?? 0
            testDbError.value = ''
          } else {
            testDbSchemas.value = []
            testDbTablesBySchema.value = {}
            testSelectedDbTable.value = ''
            testDbTableCountAvailable.value = null
            testDbTableCountTotal.value = null
          }
        } catch (e: any) {
          testDbError.value = 'Ошибка при загрузке таблиц: ' + (e && typeof e === 'object' && 'message' in e ? (e as any).message : String(e));
          testDbSchemas.value = []
          testDbTablesBySchema.value = {}
          testSelectedDbTable.value = ''
          testDbTableCountAvailable.value = null
          testDbTableCountTotal.value = null
        } finally {
          testDbTablesLoading.value = false
        }
      }
    }
    function closeTestDbModal() {
      testDbModalVisible.value = false
      testDbError.value = ''
    }
    async function loadTestTableFromDb() {
      if (!testSelectedDbTable.value || !testSelectedDbSchema.value) return
      testDbError.value = ''
      isTestLoadingFromDb.value = true
      try {
        const response = await fetch('http://localhost:8000/download-table-from-db', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
          body: JSON.stringify({ db_schema: testSelectedDbSchema.value, table: testSelectedDbTable.value })
        })
        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          testDbError.value = err.detail || 'Ошибка загрузки файла из БД.'
          return
        }
        const blob = await response.blob()
        const file = new File([blob], `${testSelectedDbTable.value}.xlsx`, { type: blob.type })
        selectedTestFile.value = file
        await processTestFile(file)
        testFileLoaded.value = true
        if (store.setSelectedTestFile) store.setSelectedTestFile(file)
        if (store.setTestFileLoaded) store.setTestFileLoaded(true)
        closeTestDbModal()
        testDownloadSuccessModalVisible.value = true
        setTimeout(() => { testDownloadSuccessModalVisible.value = false }, 1800)
      } catch (error: any) {
        testDbError.value = 'Ошибка загрузки данных из БД: ' + (error?.message || error)
      } finally {
        isTestLoadingFromDb.value = false
      }
    }
    async function fetchTestTablePreview(tableName: string) {
      if (!tableName || !testSelectedDbSchema.value) {
        testTablePreview.value = null
        return
      }
      testTablePreviewLoading.value = true
      testTablePreviewError.value = ''
      try {
        const response = await fetch('http://localhost:8000/get-table-preview', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
          body: JSON.stringify({ db_schema: testSelectedDbSchema.value, table: tableName })
        })
        const result = await response.json()
        if (result.success && Array.isArray(result.data)) {
          testTablePreview.value = result.data
        } else {
          testTablePreview.value = null
          testTablePreviewError.value = result.detail || 'Не удалось получить предпросмотр.'
        }
      } catch (e: any) {
        testTablePreview.value = null
        testTablePreviewError.value = 'Ошибка предпросмотра: ' + (e?.message || e)
      } finally {
        testTablePreviewLoading.value = false
      }
    }
    watch(testSelectedDbTable, (val) => {
      if (val) fetchTestTablePreview(val)
      else testTablePreview.value = null
    })
    // --- TEST UPLOAD TO DB MODAL LOGIC ---
    function openTestUploadToDbModal() {
      testUploadToDbModalVisible.value = true
      testUploadTableName.value = ''
      testUploadToDbError.value = ''
      testSelectedPrimaryKeys.value = []
      testDbSaveMode.value = 'new'
      testSelectedUploadDbSchema.value = ''
      if (store.dbConnected && store.authToken) {
        testUploadDbTablesLoading.value = true
        fetch('http://localhost:8000/get-tables', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${store.authToken}`
          },
        })
          .then(res => res.json())
          .then(result => {
            if (result.success) {
              testUploadDbSchemas.value = Object.keys(result.tables)
              testUploadDbTablesBySchema.value = result.tables
              testSelectedUploadDbSchema.value = testUploadDbSchemas.value[0] || ''
              testUploadTableName.value = ''
              testDbTableCountAvailable.value = result.count_available ?? 0
              testDbTableCountTotal.value = result.count_total ?? 0
            } else {
              testUploadDbSchemas.value = []
              testUploadDbTablesBySchema.value = {}
              testUploadTableName.value = ''
              testDbTableCountAvailable.value = null
              testDbTableCountTotal.value = null
            }
          })
          .catch(() => {
            testUploadDbSchemas.value = []
            testUploadDbTablesBySchema.value = {}
            testUploadTableName.value = ''
            testDbTableCountAvailable.value = null
            testDbTableCountTotal.value = null
          })
          .finally(() => { testUploadDbTablesLoading.value = false })
      } else {
        testUploadDbSchemas.value = []
        testUploadDbTablesBySchema.value = {}
        testUploadTableName.value = ''
        testDbTableCountAvailable.value = null
        testDbTableCountTotal.value = null
      }
    }
    function closeTestUploadToDbModal() {
      testUploadToDbModalVisible.value = false
      testUploadTableName.value = ''
      testUploadToDbError.value = ''
      testSelectedPrimaryKeys.value = []
    }
    async function uploadTestFileToDb() {
      if (!selectedTestFile.value || !testUploadTableName.value || !testSelectedUploadDbSchema.value) return
      testUploadToDbLoading.value = true
      testUploadToDbError.value = ''
      try {
        const formData = new FormData()
        formData.append('file', selectedTestFile.value)
        formData.append('db_schema', testSelectedUploadDbSchema.value)
        formData.append('table_name', testUploadTableName.value)
        formData.append('primary_keys', JSON.stringify(testSelectedPrimaryKeys.value))
        formData.append('dbSaveMode', testDbSaveMode.value)
        const response = await fetch('http://localhost:8000/upload-excel-to-db', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${store.authToken}`
          },
          body: formData
        })
        const result = await response.json()
        if (result.success) {
          closeTestUploadToDbModal()
          testUploadSuccessModalVisible.value = true
          setTimeout(() => { testUploadSuccessModalVisible.value = false }, 1800)
        } else {
          testUploadToDbError.value = result.detail || 'Ошибка при загрузке файла в БД.'
        }
      } catch (e: any) {
        testUploadToDbError.value = 'Ошибка: ' + (e?.message || e)
      } finally {
        testUploadToDbLoading.value = false
      }
    }
    // --- TEST DOWNLOAD ---
    const downloadTestFromApp = () => {
      if (!selectedTestFile.value) {
        alert('Нет файла для скачивания. Сначала загрузите файл вручную или из БД.');
        return;
      }
      const file = selectedTestFile.value;
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(file);
      link.download = file.name || 'downloaded_file.xlsx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    // --- Статистика и NaN для testTableData ---
    const testDescribe = computed(() => {
      if (!store.testTableData || !store.testTableData.length) return {}
      const cols = Object.keys(store.testTableData[0])
      const result: Record<string, any> = {}
      for (const col of cols) {
        const vals = store.testTableData.map(r => {
          const v = r[col]
          return (typeof v === 'number' && !isNaN(v)) ? v : (v !== null && v !== undefined && v !== '' && !isNaN(Number(v)) ? Number(v) : null)
        }).filter(v => v !== null)
        if (vals.length === 0) continue
        const sorted = [...vals].sort((a, b) => (a as number) - (b as number))
        const mean = vals.reduce((a, b) => (a as number) + (b as number), 0) / vals.length
        const std = Math.sqrt(vals.reduce((a, b) => a + Math.pow((b as number) - mean, 2), 0) / vals.length)
        const q = (p: number) => {
          const pos = (sorted.length - 1) * p
          const base = Math.floor(pos)
          const rest = pos - base
          if (sorted[base + 1] !== undefined) return sorted[base] + rest * (sorted[base + 1] - sorted[base])
          return sorted[base]
        }
        result[col] = {
          count: vals.length,
          mean: mean.toFixed(4),
          std: std.toFixed(4),
          min: Math.min(...vals),
          q25: q(0.25).toFixed(4),
          q50: q(0.5).toFixed(4),
          q75: q(0.75).toFixed(4),
          max: Math.max(...vals)
        }
      }
      return result
    })
    const testNaN = computed(() => {
      if (!store.testTableData || !store.testTableData.length) return {}
      const cols = Object.keys(store.testTableData[0])
      const result: Record<string, number> = {}
      for (const col of cols) {
        let nan = 0
        for (const row of store.testTableData) {
          const v = row[col]
          if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) nan++
        }
        result[col] = nan
      }
      return result
    })

    function onTrainAccordionClick(event: MouseEvent) {
      trainOpen.value = !trainOpen.value;
      (event.currentTarget as HTMLButtonElement | null)?.blur();
    }
    function onTestAccordionClick(event: MouseEvent) {
      testOpen.value = !testOpen.value;
      (event.currentTarget as HTMLButtonElement | null)?.blur();
    }

    return {
      fileInput,
      selectedFile,
      isLoading,
      chunkSize,
      handleDrop,
      handleFileChange,
      handleUpload,
      dbModalVisible,
      openDbModal,
      closeDbModal,
      selectedDbTable,
      isLoadingFromDb,
      dbError,
      loadTableFromDb,
      dbConnected,
      dbTablesLoading, // <--- export
      tablePreview,
      tablePreviewLoading,
      tablePreviewError,
      uploadToDbModalVisible,
      uploadTableName,
      uploadToDbLoading,
      uploadToDbError,
      openUploadToDbModal,
      closeUploadToDbModal,
      uploadFileToDb,
      fileLoaded,
      uploadSuccessModalVisible,
      downloadSuccessModalVisible,
      selectedPrimaryKeys,
      dbSaveMode,
      tableData,
      uploadDbTables,
      uploadDbTablesLoading,
      dbTableCountAvailable,
      dbTableCountTotal,
      dbSchemas,
      selectedDbSchema,
      dbTablesBySchema,
      filteredDbTables,
      uploadDbSchemas,
      selectedUploadDbSchema,
      uploadDbTablesBySchema,
      filteredUploadDbTables,
      // --- TEST DATA ---
      testFileInput,
      selectedTestFile,
      isTestLoading,
      testFileLoaded,
      handleTestFileChange,
      handleTestDrop,
      handleTestUpload,
      // --- TEST DB ---
      testDbModalVisible,
      openTestDbModal,
      closeTestDbModal,
      testSelectedDbTable,
      isTestLoadingFromDb,
      testDbError,
      loadTestTableFromDb,
      testDbSchemas,
      testDbTablesBySchema,
      testSelectedDbSchema,
      filteredTestDbTables,
      testDbTablesLoading,
      testTablePreview,
      testTablePreviewLoading,
      testTablePreviewError,
      // --- TEST UPLOAD TO DB ---
      testUploadToDbModalVisible,
      testUploadTableName,
      testUploadToDbLoading,
      testUploadToDbError,
      openTestUploadToDbModal,
      closeTestUploadToDbModal,
      uploadTestFileToDb,
      testUploadSuccessModalVisible,
      testDownloadSuccessModalVisible,
      testSelectedPrimaryKeys,
      testDbSaveMode,
      testUploadDbTables,
      testUploadDbTablesLoading,
      testDbTableCountAvailable,
      testDbTableCountTotal,
      testUploadDbSchemas,
      testSelectedUploadDbSchema,
      testUploadDbTablesBySchema,
      filteredTestUploadDbTables,
      // --- DOWNLOAD BUTTONS ---
      downloadFromApp,
      downloadTestFromApp,
      // Accordion
      trainOpen,
      testOpen,
      store,
      onTrainAccordionClick,
      onTestAccordionClick,
    }
  }
})
</script>

<style scoped>
.file-uploader {
  margin-top: 1rem;
}

.section-title {
  font-size: 1.1rem;
  color: #333;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #2196F3;
}

.settings-panel {
  margin-bottom: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
}

.settings-summary {
  padding: 0.75rem;
  cursor: pointer;
  font-weight: 500;
  color: #333;
}

.settings-content {
  padding: 1rem;
  border-top: 1px solid #ddd;
}

.input-label {
  display: block;
  color: #666;
  margin-bottom: 0.5rem;
  font-size: 0.97rem;
  padding: 0;
}

.db-modal-content .input-label {
  margin-top: 0;
  font-size: 0.97rem;
  padding: 0;
}

.db-modal-content .db-input {
  padding: 0.45rem 0.6rem;
  margin-bottom: 0.5rem;
  font-size: 0.97rem;
}

.number-input {
  width: 100%;
  padding: 0.5rem;
  margin-top: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.upload-zone {
  border: 2px dashed #ccc;
  border-radius: 4px;
  padding: 20px;
  text-align: center;
  background-color: #fafafa;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-zone:hover {
  border-color: #2196f3;
  background-color: #f0f7ff;
}

.file-info {
  margin: 0.5rem 0;
  padding: 0.5rem;
  background-color: #e3f2fd;
  border-radius: 4px;
  color: #1976d2;
  font-size: 0.9rem;
}

.upload-button {
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

.upload-button:hover:not(:disabled) {
  background-color: #1976d2;
}

.upload-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button {
  padding: 10px 20px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 10px;
  transition: background-color 0.2s;
}

.connect-btn {
  margin-bottom: 0px;
}

.choose-file-btn {
  padding: 10px 20px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 10px;
  transition: background-color 0.2s;
}
.choose-file-btn:hover {
  background-color: #1976D2;
}

button:hover {
  /* убираем глобальный hover-стиль */
  background-color: unset;
}

.subsection-title {
  font-size: 1rem;
  color: #666;
  margin: 1rem 0 0.5rem;
}

.spinner-wrap {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #2196F3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;
  vertical-align: middle;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

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
  max-width: 700px;
  min-width: 500px;
  width: 100%;
  min-height: 600px; /* was 600px, increased for more rows */
  max-height: 100vh;
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
  /* убираем любые эффекты фона */
}
.close-btn:active, .close-btn:focus {
  background: none !important;
  outline: none;
  box-shadow: none;
}

.db-input {
  width: 100%;
  padding: 0.75rem;
  margin-top: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.connect-btn {
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

.error-message {
  margin-top: 1rem;
  color: #f44336;
  font-size: 0.9rem;
}

.db-load-btn {
  width: 100%;
  padding: 0.75rem;
  background-color: #388e3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  margin-bottom: 10px;
  transition: background-color 0.2s;
}
.db-load-btn:hover {
  background-color: #256b27 !important;
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
  margin-bottom: 10px;
  transition: background-color 0.2s;
}
.upload-to-db-btn:hover {
  background-color: #0d47a1 !important;
}

/* Стили для анимации загрузки */
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

/* Новые стили для модального окна */
.db-modal-content {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-preview-fixed {
  min-height: 215px;
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  position: relative;
}
.table-preview-scroll {
  flex: 1 1 auto;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background: #fafbfc;
}

.db-modal-footer {
  flex-shrink: 0;
  margin-top: auto;
  padding-top: 1rem;
  background: white;
  position: sticky;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 2;
}

.db-modal-table-area {
  min-height: 180px; /* was 110px */
  max-height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  margin-bottom: 1rem;
}

/* Стили для модального окна успешной загрузки */
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

#upload-to-db-modal {
  min-width: 320px;
  max-width: 420px;
  min-height: 220px;
  max-height: 90vh;
  padding: 1.2rem 1.2rem 1rem 1.2rem;
  box-sizing: border-box;
  font-size: 0.98rem;
  display: flex;
  flex-direction: column;
}

.db-modal.upload-to-db-modal,
.db-modal#test-upload-to-db-modal {
  width: 480px;
  max-width: 95vw;
  min-width: 320px;
}

.upload-to-db-modal-test {  
  min-height: 220px;
}

.upload-to-db-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  min-height: 48px;
}

.upload-to-db-error-area {
  min-height: 1.5em;
  margin-top: 0.7rem;
  font-size: 0.95rem;
  color: #f44336;
  text-align: center;
  word-break: break-word;
}

.table-count-info {
  font-size: 0.88rem;
  color: #1976d2;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.table-preview-placeholder {
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
  font-size: 1.05rem;
  text-align: center;
  min-height: 100px;
}

.download-from-app-btn {
  width: 100%;
  padding: 0.75rem;
  background-color: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  margin-bottom: 10px;
  transition: background-color 0.2s;
  box-sizing: border-box;
  display: block;
}
.download-from-app-btn:hover:not(:disabled) {
  background-color: #0d47a1;
}

/* Аккордеон */
.accordion-section {
  margin-bottom: 1.2rem;
}
.accordion-toggle {
  width: 100%;
  text-align: left;
  border: none;
  outline: none;
  font-size: 1.13rem;
  font-weight: 700;
  color: #fff;
  padding: 0.95rem 1.2rem;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.7em;
  transition: background 0.2s, color 0.2s, box-shadow 0.2s;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.07);
  margin-bottom: 0.5rem;
  letter-spacing: 0.01em;
  font-family: 'Montserrat', 'Segoe UI Semibold', 'Arial', sans-serif;
  background: #2196f3;
}
.train-toggle,

.test-toggle {
  background: #2196f3;
}
.train-toggle:hover, .train-toggle:focus,
.test-toggle:hover, .test-toggle:focus {
  background: #1976d2;
}
.accordion-toggle:focus-visible,
.train-toggle:focus-visible,
.test-toggle:focus-visible {
  outline: 2px solid #1976d2;
  outline-offset: 2px;
}

.accordion-content {
  overflow: hidden;
  padding: 0;
  background: transparent;
}
.accordion-inner {
  padding: 0.5rem 0 0.5rem 0.5rem;
  background: transparent;
  color: inherit;
}
.accordion-fade-enter-active, .accordion-fade-leave-active {
  transition: height 0.35s cubic-bezier(0.4, 0.0, 0.2, 1), opacity 0.3s;
}
.accordion-fade-enter-from, .accordion-fade-leave-to {
  height: 0;
   opacity: 0;
}
.accordion-fade-enter-to, .accordion-fade-leave-from {
  height: auto;
  opacity: 1;
}
</style>