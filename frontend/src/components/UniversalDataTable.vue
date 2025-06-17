<template>  <div class="data-table-block" v-if="data && data.length">
    <div class="success-banner" :style="bannerStyle">
      {{ title }} загружены! Строк: {{ totalRows }}, колонок: {{ columns.length }}
    </div>
    <DataTable :data="data" :customTitle="statsTitle" />
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue'
import DataTable from './DataTable.vue'

export default defineComponent({
  name: 'UniversalDataTable',
  components: { DataTable },
  props: {
    data: {
      type: Array,
      required: true
    },
    title: {
      type: String,
      required: true
    },
    statsTitle: {
      type: String,
      default: ''
    },
    bannerStyle: {
      type: Object,
      default: () => ({})
    }
  },
  setup(props) {
    const columns = computed(() => {
      return props.data.length > 0 ? Object.keys(props.data[0] as Record<string, any>) : []
    })
    const totalRows = computed(() => props.data.length)
    return { columns, totalRows }
  }
})
</script>

<style scoped>
.data-table-block {
  margin-bottom: 2rem;
}
.success-banner {
  width: 100%;
  padding: 1rem;
  background-color: #4CAF50;
  color: white;
  text-align: center;
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 1rem;
  border-radius: 4px;
  box-sizing: border-box;
}
</style>
