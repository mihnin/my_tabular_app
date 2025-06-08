<template>
  <div class="page-content">
    <!-- Показываем Train/Test/график только если нет leaderboard -->
    <template v-if="!store.trainingStatus || !store.trainingStatus.leaderboard || !Array.isArray(store.trainingStatus.leaderboard) || store.trainingStatus.leaderboard.length === 0">
      <UniversalDataTable
        v-if="store.tableData.length"
        :data="store.tableData"
        title="Train"
        statsTitle="Статистика Train"
      />
      <hr v-if="store.tableData.length && store.testFileLoaded && store.testTableData && store.testTableData.length" class="data-separator" />
      <div
        v-if="store.testFileLoaded && store.testTableData && store.testTableData.length"
        ref="testTableBlock"
        :key="store.testTableData.length + '-' + (store.testTableData[0] ? Object.keys(store.testTableData[0]).join(',') : '')"
      >
        <UniversalDataTable
          :data="store.testTableData"
          title="Test"
          statsTitle="Статистика Test"
          :bannerStyle="{ backgroundColor: '#1976d2' }"
        />
      </div>
      <template v-if="store.dateColumn !== '<нет>' && store.targetColumn !== '<нет>' && store.tableData.length">
        <TimeSeriesChart
          :data="store.tableData.slice(0, 1000)"
          :dateColumn="store.dateColumn"
          :targetColumn="store.targetColumn"
          :idColumn="store.idColumn !== '<нет>' ? store.idColumn : undefined"
        />
      </template>
    </template>

    <!-- Лидерборд показываем если он есть -->
    <div v-if="store.sessionId && store.trainingStatus && store.trainingStatus.leaderboard && Array.isArray(store.trainingStatus.leaderboard)">
      <div class="leaderboard-table-main">
        <h4>Лидерборд моделей</h4>
        <table v-if="store.trainingStatus.leaderboard.length > 0 && typeof store.trainingStatus.leaderboard[0] === 'object' && store.trainingStatus.leaderboard[0] !== null">
          <thead>
            <tr>
              <th v-for="(value, key) in store.trainingStatus.leaderboard[0]" :key="key">{{ key }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in store.trainingStatus.leaderboard" :key="idx"
                @click="row.strategy === 'pycaret' && store.trainingStatus.pycaret ? openPycaretModal() : null"
                :style="row.strategy === 'pycaret' && store.trainingStatus.pycaret ? 'cursor:pointer;background:#f5f5f5;' : ''">
              <td v-for="(value, key) in row" :key="key">{{ formatCellValue(value) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-leaderboard-message" style="padding: 1rem; color: #f44336; text-align: center;">
          Никакая модель не обучилась. Проверьте, есть ли выбранные модели и попробуйте увеличить лимит по времени.
        </div>
      </div>
      <!-- Feature Importance Table -->
      <div class="leaderboard-table-main feature-importance-table-main" style="margin-top:2.5rem;">
        <h4>Значимость признаков</h4>
        <table v-if="store.trainingStatus && store.trainingStatus.feature_importance && store.trainingStatus.feature_importance.length > 0 && typeof store.trainingStatus.feature_importance[0] === 'object' && store.trainingStatus.feature_importance[0] !== null">
          <thead>
            <tr>
              <th v-for="(value, key) in store.trainingStatus.feature_importance[0]" :key="key">{{ key }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in store.trainingStatus.feature_importance" :key="idx">
              <td v-for="(value, key) in row" :key="key">{{ formatCellValue(value) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-leaderboard-message" style="padding: 1rem; color: #f44336; text-align: center;">
          Нет данных о значимости признаков.
        </div>
      </div>
    </div>

    <!-- Модальное окно PyCaret лидербордов -->
    <div v-if="pycaretModalVisible" class="pycaret-modal-overlay" @click="closePycaretModal">
      <div class="pycaret-modal" @click.stop>
        <button class="close-btn" @click="closePycaretModal">×</button>
        <h3 style="margin-bottom:1rem">{{ pycaretModalTitle }}</h3>
        <div v-if="pycaretLeaderboards && typeof pycaretLeaderboards === 'object'">
          <div v-for="(lbArr, id) in pycaretLeaderboards" :key="id" class="pycaret-leaderboard-block">
            <h4>ID: {{ id }}</h4>
            <div v-if="Array.isArray(lbArr) && lbArr.length">
              <table v-if="typeof lbArr[0] === 'object' && lbArr[0] !== null">
                <thead>
                  <tr>
                    <th v-for="(value, key) in lbArr[0]" :key="key">{{ key }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ridx) in lbArr" :key="ridx">
                    <td v-for="(value, key) in row" :key="key">{{ formatCellValue(value) }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else style="color:#f44336; text-align:center; padding:0.5rem;">Нет данных по моделям</div>
            </div>
            <div v-else style="color:#f44336; text-align:center; padding:0.5rem;">Нет данных по моделям</div>
          </div>
        </div>
        <div v-else style="color:#f44336; text-align:center;">Нет данных PyCaret</div>
      </div>
    </div>

    <!-- Уведомление об успешном прогнозе -->
    <div v-if="Array.isArray(store.predictionRows) && store.predictionRows.length > 0 && typeof store.predictionRows[0] === 'object' && store.predictionRows[0] !== null" class="success-banner">
      Прогноз успешно выполнен! Можете скачать таблицу с прогнозом в панели слева.
    </div>

    <div v-if="Array.isArray(store.predictionRows) && store.predictionRows.length > 0 && typeof store.predictionRows[0] === 'object' && store.predictionRows[0] !== null" ref="predictionTableBlock">
      <div class="prediction-table limited-height">
        <h4>Первые 10 строк прогноза</h4>
        <table>
          <thead>
            <tr>
              <th v-for="headerKey in Object.keys(store.predictionRows[0])" :key="headerKey" style="text-align: center;">{{ headerKey }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in store.predictionRows" :key="row.item_id + '-' + row.timestamp">
              <td v-for="cellHeaderKey in Object.keys(row)" :key="cellHeaderKey"
                  :style="{ minWidth: (getColWidth(cellHeaderKey) * 1.1) + 'ch', textAlign: 'center' }">
                <template v-if="cellHeaderKey.toLowerCase().includes('date') || cellHeaderKey.toLowerCase().includes('timestamp')">
                  {{ typeof row[cellHeaderKey] === 'string' ? row[cellHeaderKey].split(' ')[0] : row[cellHeaderKey] }}
                </template>
                <template v-else>
                  {{ formatCellValue(row[cellHeaderKey]) }}
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, nextTick, ref, watch } from 'vue'
import { useMainStore } from '../stores/mainStore'
import DataTable from '../components/DataTable.vue'
import UniversalDataTable from '../components/UniversalDataTable.vue'
import TimeSeriesChart from '../components/TimeSeriesChart.vue'

export default defineComponent({
  name: 'MainPage',
  components: {
    DataTable,
    UniversalDataTable,
    TimeSeriesChart
  },
  setup() {
    const store = useMainStore()
    const predictionTableBlock = ref<HTMLElement | null>(null)
    const testTableBlock = ref<HTMLElement | null>(null)

    // Модалка для PyCaret лидербордов
    const pycaretModalVisible = ref(false)
    const pycaretLeaderboards = ref<any>(null)
    const pycaretModalTitle = ref('')

    // Функция для открытия модалки
    function openPycaretModal() {
      pycaretLeaderboards.value = store.trainingStatus?.pycaret || null
      pycaretModalVisible.value = true
      pycaretModalTitle.value = 'Лидерборды PyCaret'
    }
    function closePycaretModal() {
      pycaretModalVisible.value = false
    }

    // Функция для оценки ширины столбца по длине заголовка и первой строки
    function getColWidth(headerKey: string): number {
      const firstRow = store.predictionRows[0]?.[headerKey];
      const headerLen = headerKey.length;
      const valueLen = firstRow ? String(firstRow).length : 0;
      return Math.max(headerLen, valueLen, 8); // минимум 8 символов
    }

    // Форматирование дробных значений до 2 знаков после запятой
    function formatCellValue(val: any) {
      if (typeof val === 'number' && !Number.isInteger(val)) {
        return val.toFixed(2)
      }
      return val
    }

    // Скроллим к таблице прогноза при появлении новых predictionRows
    watch(
      () => store.predictionRows,
      (val) => {
        if (val && val.length > 0) {
          nextTick(() => {
            if (predictionTableBlock.value) {
              predictionTableBlock.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
          })
        }
      },
      { deep: true }
    )

    // Скроллим к таблице теста при появлении новых testTableData
    watch(
      () => [store.testFileLoaded, store.testTableData.length],
      async ([loaded, len], [oldLoaded, oldLen]) => {
        if (loaded && typeof len === 'number' && len > 0) {
          await nextTick()
          if (testTableBlock.value) {
            testTableBlock.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
        }
      },
      { immediate: false }
    )
    return { store, predictionTableBlock, testTableBlock, getColWidth, formatCellValue, pycaretModalVisible, pycaretLeaderboards, openPycaretModal, closePycaretModal, pycaretModalTitle }
  }
})
</script>

<style scoped>
.page-content {
  flex: 1;
  width: 100%;
  min-width: 0;
  padding: 1rem;
}
.page-content > div {
  display: flex;
  flex-direction: column;
}
.success-banner {
  width: 100%;
  padding: 1rem;
  background-color: #4CAF50;
  color: white;
  text-align: center;
  font-size: 1rem;
  font-weight: 500;
  margin: 1.5rem 0 1.5rem 0;
  border-radius: 4px;
  box-sizing: border-box;
}

.pycaret-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.35);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pycaret-modal {
  background: #fff;
  border-radius: 8px;
  padding: 2rem 2rem 1.5rem 2rem;
  min-width: 340px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 32px rgba(0,0,0,0.18);
  position: relative;
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
.close-btn:hover {
  color: #d32f2f;
}
.pycaret-leaderboard-block {
  margin-bottom: 2rem;
}
.pycaret-leaderboard-block table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0.5rem;
}
.pycaret-leaderboard-block th, .pycaret-leaderboard-block td {
  border: 1px solid #e0e0e0;
  padding: 0.4rem 0.7rem;
  text-align: center;
  font-size: 0.97rem;
}
.pycaret-leaderboard-block th {
  background: #f5f5f5;
  font-weight: 600;
}
.data-separator {
  border: none;
  border-top: 2px solid #1976d2;
  margin: 2.5rem 0 2.5rem 0;
}
.leaderboard-table-main {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
  padding: 2rem 2rem 1.5rem 2rem;
}
.leaderboard-table-main h4 {
  font-size: 1.18rem;
  font-weight: 600;
  margin-bottom: 1.2rem;
  color: #1976d2;
}
.leaderboard-table-main table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 0.5rem;
}
.leaderboard-table-main th, .leaderboard-table-main td {
  border: 1px solid #e0e0e0;
  padding: 0.5rem 0.8rem;
  text-align: center;
  font-size: 0.97rem;
}
.leaderboard-table-main th {
  background: #f5f5f5;
  font-weight: 600;
}
.feature-importance-table-main {
  margin-top: 2.5rem;
}
</style>
