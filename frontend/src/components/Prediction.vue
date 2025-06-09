<template>
  <div class="prediction" v-if="isVisible">
    <h3 class="section-title">Прогноз</h3>
    
    <button 
      @click="makePrediction"
      class="predict-button"
      :disabled="!canMakePrediction || isLoading"
    >
      <span v-if="isLoading" class="loader"></span>
      <span v-else>📊 Сделать прогноз</span>
    </button>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, ref } from 'vue'
import { useMainStore } from '../stores/mainStore'

export default defineComponent({
  name: 'Prediction',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const store = useMainStore();
    const isLoading = ref(false); // Local loading state for the button

    const canMakePrediction = computed(() => {
      return (
        store.sessionId &&
        store.trainingStatus &&
        store.trainingStatus.status === 'completed' &&
        store.trainingStatus.leaderboard
      );
    });

    const makePrediction = async () => {
      const sessionId = store.sessionId;
      if (!sessionId) {
        alert('Сначала обучите модель. Session ID не найден.');
        return;
      }
      isLoading.value = true;
      try {
        // Fetch only the preview (first 10 rows) as JSON
        const response = await fetch(`http://localhost:8000/predict_head/${sessionId}`);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error('Ошибка при получении превью прогноза: ' + errorText);
        }
        const data = await response.json();
        if (data && Array.isArray(data.prediction_head)) {
          store.setPredictionRows(data.prediction_head);
        } else {
          store.setPredictionRows([]);
        }
      } catch (error) {
        alert(`Ошибка при получении превью прогноза: ${error instanceof Error ? error.message : String(error)}`);
        store.setPredictionRows([]);
      } finally {
        setTimeout(() => { isLoading.value = false; }, 300);
      }
    };

    return {
      canMakePrediction,
      makePrediction,
      isLoading,
      store // if needed in template
    };
  }
});
</script>

<style scoped>
.prediction {
  margin-top: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
  color: #333;
}

.predict-button {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  font-weight: 500;
  color: white;
  background-color: #1976d2;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  position: relative;
}

.predict-button:hover:not(:disabled) {
  background-color: #1565c0;
}

.predict-button:disabled {
  background-color: #bbdefb;
  cursor: not-allowed;
}

.loader {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid #1976d2;
  border-radius: 50%;
  border-top: 3px solid #bbdefb;
  animation: spin 1s linear infinite;
  vertical-align: middle;
  margin-right: 8px;
}

.prediction-table {
  margin-top: 2rem;
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  overflow-x: auto;
  padding: 1.5rem 1rem 1.5rem 1rem;
}
.prediction-table h4 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1976d2;
  letter-spacing: 0.5px;
}
.prediction-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 1rem;
}
.prediction-table th, .prediction-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}
.prediction-table th {
  background-color: #f5f7fa;
  font-weight: 700;
  color: #333;
  border-top: 1px solid #e0e0e0;
}
.prediction-table tr:hover {
  background-color: #f0f7ff;
}
.prediction-table td {
  color: #222;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
