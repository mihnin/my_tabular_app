<template>
  <div class="column-selector" v-if="isVisible">
    <h3 class="section-title">Настройки задачи</h3>
    <!-- Целевая колонка -->
    <div class="column-select">
      <label>Целевая колонка (target)</label>
      <select v-model="selectedTargetColumn">
        <option value="<нет>">&lt;нет&gt;</option>
        <option v-for="column in availableColumns" :key="column" :value="column">
          {{ column }}
        </option>
      </select>
    </div>
    <!-- Тип задачи -->
    <div class="column-select">
      <label>Тип задачи</label>
      <select v-model="selectedTaskType">
        <option value="auto">auto (автоопределение)</option>
        <option value="binary">binary (двоичная классификация)</option>
        <option value="multiclass">multiclass (мультиклассовая классификация)</option>
        <option value="regression">regression (регрессия)</option>
      </select>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue'
import { useMainStore } from '../stores/mainStore'

export default defineComponent({
  name: 'ColumnSelector',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const store = useMainStore()
    const selectedTargetColumn = computed({
      get: () => store.targetColumn,
      set: (value: string) => store.setTargetColumn(value)
    })
    const selectedTaskType = computed({
      get: () => store.problemType || 'auto',
      set: (value: string) => store.setProblemType(value)
    })
    const availableColumns = computed(() => {
      if (!store.tableData.length) return []
      return Object.keys(store.tableData[0])
    })
    return {
      selectedTargetColumn,
      selectedTaskType,
      availableColumns
    }
  }
})
</script>

<style scoped>
.column-selector {
  margin-top: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
  color: #333;
}

.column-select {
  margin-bottom: 1rem;
}

.column-select label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
}

.column-select select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  font-size: 1rem;
}
</style>