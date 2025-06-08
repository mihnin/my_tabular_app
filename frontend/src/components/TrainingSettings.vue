<template>
  <div class="training-settings">
    <FileUploader @file-loaded="handleFileLoaded" />
    <!-- DataTable и page-content убраны отсюда, их нужно размещать в MainPage.vue -->
    <ColumnSelector :is-visible="hasLoadedFile" />
    <MissingValueHandler 
      :is-visible="hasLoadedFile" 
      :available-static-features="staticFeatures"
    />
    <FrequencySettings :is-visible="hasLoadedFile" />
    <MetricsAndModels :is-visible="hasLoadedFile" />
    <Training :is-visible="hasLoadedFile" />
    <Prediction :is-visible="hasLoadedFile" />
    <SaveResults :is-visible="hasLoadedFile" />
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue'
import { useMainStore } from '../stores/mainStore'
import FileUploader from './FileUploader.vue'
import ColumnSelector from './ColumnSelector.vue'
import MissingValueHandler from './MissingValueHandler.vue'
import FrequencySettings from './FrequencySettings.vue'
import MetricsAndModels from './MetricsAndModels.vue'
import Training from './Training.vue'
import Prediction from './Prediction.vue'
import SaveResults from './SaveResults.vue'

export default defineComponent({
  name: 'TrainingSettings',
  
  components: {
    FileUploader,
    ColumnSelector,
    MissingValueHandler,
    FrequencySettings,
    MetricsAndModels,
    Training,
    Prediction,
    SaveResults
  },

  setup() {
    const store = useMainStore()

    const hasLoadedFile = computed(() => 
      store.tableData.length > 0 && 
      store.fileLoaded &&
      store.testFileLoaded
    )
    const staticFeatures = computed(() => store.staticFeatures)

    const handleFileLoaded = () => {
      // Reset any previous selections
      store.setDateColumn('<нет>')
      store.setTargetColumn('<нет>')
      store.setIdColumn('<нет>')
      store.setStaticFeatures([])
      store.setFillMethod('mean')
      store.setGroupingColumns([])
      store.setSelectedMetric('MAE (Mean absolute error)')
      store.setSelectedModels(['*'])
      store.setSelectedPreset('high_quality')
      store.setTimeLimit(null)
      store.setMeanOnly(false)
      store.setTrainPredictSave(true)
    }

    return {
      hasLoadedFile,
      staticFeatures,
      handleFileLoaded,
      store
    }
  }
})
</script>

<style scoped>
.training-settings {
  width: 100%;
}
</style>