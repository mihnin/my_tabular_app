<template>
  <div class="metrics-and-models" v-if="isVisible">
    <h3 class="section-title">Метрика и модели</h3>
    
    <!-- Выбор метрики -->
    <div class="metric-select">
      <label>Метрика</label>
      <select v-model="selectedMetric">
        <option 
          v-for="metric in availableMetrics" 
          :key="metric.key" 
          :value="metric.key"
        >
          {{ metric.label }}
        </option>
      </select>
    </div>

    <!-- Выбор моделей -->
    <div class="models-select">
      <label>Модели AutoGluon</label>
      <div class="selected-models">
        <div 
          v-for="model in selectedModels" 
          :key="model" 
          class="model-tag"
        >
          {{ model === '*' ? 'Все модели' : getModelDescription(model) }}
          <button @click="removeModel(model)" class="remove-model">×</button>
        </div>
      </div>
      <select 
        v-model="selectedModel"
        @change="addModel"
      >
        <option value="">Выберите модель</option>
        <option value="*" v-if="!selectedModels.includes('*')">Все модели</option>
        <option 
          v-for="(description, key) in agModels" 
          :key="key" 
          :value="key"
          :disabled="selectedModels.includes(key)"
        >
          {{ description }}
        </option>
      </select>
    </div>

    <!-- Пресет -->
    <div class="preset-select">
      <label>Пресет AutoGluon</label>
      <select v-model="selectedPreset">
        <option 
          v-for="preset in presetsList" 
          :key="preset" 
          :value="preset"
        >
          {{ preset }}
        </option>
      </select>
    </div>

    <!-- Лимит по времени -->
    <div class="time-limit-input">
      <label>Лимит по времени (сек)</label>
      <input 
        type="number" 
        v-model.number="timeLimit"
        min="1"
        placeholder="Без лимита"
      >
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch, onMounted } from 'vue'
import { useMainStore } from '../stores/mainStore'

const metricsByTask: Record<string, string[]> = {
  auto: [
    'accuracy', 'balanced_accuracy', 'roc_auc', 'f1', 'precision', 'recall', 'log_loss', 'average_precision',
    'root_mean_squared_error', 'mean_squared_error', 'mean_absolute_error', 'r2', 'pearsonr', 'spearmanr'
  ],
  binary: [
    'accuracy', 'balanced_accuracy', 'roc_auc', 'f1', 'precision', 'recall', 'log_loss', 'average_precision'
  ],
  multiclass: [
    'accuracy', 'balanced_accuracy', 'f1', 'precision', 'recall', 'log_loss'
  ],
  regression: [
    'root_mean_squared_error', 'mean_squared_error', 'mean_absolute_error', 'r2', 'pearsonr', 'spearmanr'
  ]
}

const metricsDict: Record<string, string> = {
  accuracy: 'Accuracy',
  balanced_accuracy: 'Balanced Accuracy',
  roc_auc: 'ROC AUC',
  f1: 'F1',
  precision: 'Precision',
  recall: 'Recall',
  log_loss: 'LogLoss',
  average_precision: 'AvgPrecision',
  root_mean_squared_error: 'RMSE',
  mean_squared_error: 'MSE',
  mean_absolute_error: 'MAE',
  r2: 'R²',
  pearsonr: 'PearsonR',
  spearmanr: 'SpearmanR'
}

export default defineComponent({
  name: 'MetricsAndModels',
  
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },

  setup() {
    const store = useMainStore()
    const selectedModel = ref('')
    const selectedTaskType = computed({
      get: () => store.problemType || 'auto',
      set: (value: string) => store.setProblemType(value || 'auto')
    })

    // Доступные метрики в зависимости от задачи
    const availableMetrics = computed(() => {
      const task = selectedTaskType.value;
      const allowed = metricsByTask[task] || metricsByTask['auto'];
      return allowed.map(key => ({ key, label: metricsDict[key] || key }));
    });

    const selectedMetric = computed({
      get: () => store.selectedMetric,
      set: (val: string) => store.setSelectedMetric(val)
    })

    // Если выбранная метрика не входит в доступные для задачи, выбираем MSE если доступен, иначе первую
    watch([selectedTaskType, selectedMetric], ([task, metric], [oldTask, oldMetric]) => {
      const allowed = metricsByTask[task] || metricsByTask['auto']
      if (!allowed.includes(metric)) {
        // Пытаемся выбрать MSE по умолчанию, если доступен
        const defaultMetric = allowed.includes('mean_squared_error') ? 'mean_squared_error' : allowed[0]
        store.setSelectedMetric(defaultMetric)
      }
    })

    // Инициализация метрики по умолчанию при монтировании
    onMounted(() => {
      const currentTask = selectedTaskType.value
      const allowed = metricsByTask[currentTask] || metricsByTask['auto']
      
      // Если метрика не задана или не доступна для текущей задачи, устанавливаем MSE
      if (!store.selectedMetric || !allowed.includes(store.selectedMetric)) {
        const defaultMetric = allowed.includes('mean_squared_error') ? 'mean_squared_error' : allowed[0]
        store.setSelectedMetric(defaultMetric)
      }
    })

    const agModels: Record<string, string> = {
      CAT: 'CatBoost',
      GBM: 'LightGBM',
      RF: 'RandomForestGini',
      XT: 'ExtraTreesGini',
      XGB: 'XGBoost',
      FASTAI: 'NeuralNetFastAI',
      NN_TORCH: 'PyTorchNN',
      LR: 'Linear scikit',
      KNN: 'KNearestNeighbors'
    }

    const presetsList = [
      'medium_quality',
      'high_quality',
      'best_quality',
      'good_quality',
      'optimize_for_deployment',
      'experimental'
    ]

    const selectedModels = computed({
      get: () => store.selectedModels,
      set: (value: string[]) => store.setSelectedModels(value)
    })

    const selectedPreset = computed({
      get: () => store.selectedPreset,
      set: (value: string) => store.setSelectedPreset(value)
    })

    const timeLimit = computed({
      get: () => store.timeLimit,
      set: (value: number | null) => store.setTimeLimit(value)
    })

    const getModelDescription = (modelName: string): string => {
      return modelName in agModels ? agModels[modelName] : modelName
    }

    const addModel = () => {
      if (selectedModel.value) {
        if (selectedModel.value === '*') {
          store.setSelectedModels(['*'])
        } else if (selectedModels.value.includes('*')) {
          store.setSelectedModels([selectedModel.value])
        } else {
          store.setSelectedModels([...selectedModels.value, selectedModel.value])
        }
        selectedModel.value = ''
      }
    }

    const removeModel = (model: string) => {
      store.setSelectedModels(selectedModels.value.filter(m => m !== model))
    }

    return {
      metricsDict,
      agModels,
      presetsList,
      availableMetrics,
      selectedMetric,
      selectedTaskType,
      selectedModel,
      selectedModels,
      selectedPreset,
      timeLimit,
      getModelDescription,
      addModel,
      removeModel
    }
  }
})
</script>

<style scoped>
.metrics-and-models {
  margin-top: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
  color: #333;
}

.metric-select,
.models-select,
.preset-select,
.horizon-input,
.time-limit-input {
  margin-bottom: 1rem;
}

.metric-select label,
.models-select label,
.preset-select label,
.horizon-input label,
.time-limit-input label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
}

select,
input[type="number"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  font-size: 1rem;
}

input[type="number"].invalid {
  border-color: #d32f2f;
}

.selected-models {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.model-tag {
  display: inline-flex;
  align-items: center;
  background-color: #e3f2fd;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.9rem;
  color: #1976d2;
}

.remove-model {
  background: none;
  border: none;
  color: #666;
  margin-left: 0.5rem;
  cursor: pointer;
  padding: 0 0.25rem;
}

.remove-model:hover {
  color: #d32f2f;
}

select:disabled,
input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}
</style>
