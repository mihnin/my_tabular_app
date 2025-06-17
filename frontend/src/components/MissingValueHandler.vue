<template>
  <div class="missing-value-handler" v-if="isVisible">
    <h3 class="section-title">Обработка пропусков</h3>
    
    <!-- Способ заполнения пропусков -->
    <div class="fill-method-select">
      <label>Способ заполнения пропусков</label>
      <select v-model="selectedFillMethod">
        <option 
          v-for="option in fillOptions" 
          :key="option" 
          :value="option"
        >
          {{ option }}
        </option>
      </select>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue'
import { useMainStore } from '../stores/mainStore'

export default defineComponent({
  name: 'MissingValueHandler',
  
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    availableStaticFeatures: {
      type: Array as () => string[],
      required: true
    }
  },

  setup() {
    const store = useMainStore()
    // fillOptions только новые методы
    const fillOptions = [
      'None',
      'constant=0',
      'mean',
      'median',
      'mode'
    ]
    // Дефолт — mean
    if (!store.fillMethod || !fillOptions.includes(store.fillMethod)) {
      store.setFillMethod('mean')
    }
    const selectedFillMethod = computed({
      get: () => store.fillMethod || 'mean',
      set: (value: string) => store.setFillMethod(value)
    })
    return {
      fillOptions,
      selectedFillMethod
    }
  }
})
</script>

<style scoped>
.missing-value-handler {
  margin-top: 2rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
  color: #333;
}

.fill-method-select {
  margin-bottom: 1rem;
}

.fill-method-select label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
}

select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  font-size: 1rem;
}

select:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}
</style>
