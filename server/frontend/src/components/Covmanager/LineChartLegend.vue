<template>
  <div class="legend">
    <div class="legend-container">
      <div
        v-for="dataset in datasets"
        :key="dataset.id"
        class="legend-item"
        :style="{
          cursor: 'pointer',
        }"
        @click="toggleDataset(dataset.id)"
      >
        <span
          class="legend-box"
          :style="{ borderColor: dataset?.borderColor }"
        ></span>
        <label
          class="legend-label"
          :style="{
            textDecoration: dataset.hidden ? 'line-through' : 'none',
          }"
          >{{ dataset.label }}</label
        >
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, toRefs } from "vue";

export default defineComponent({
  name: "LineChartLegend",
  props: {
    datasets: {
      type: Array,
      required: true,
    },
    onToggle: {
      type: Function,
      required: true,
    },
  },
  setup(props) {
    const { onToggle } = toRefs(props);

    const toggleDataset = (id) => {
      onToggle.value(id); // Trigger the parent handler to update the Set
    };

    return {
      toggleDataset,
    };
  },
});
</script>

<style scoped>
.legend {
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 8px 0px;
}
.legend .legend-container {
  display: flex;
  gap: 12px;
}
.legend .legend-item {
  display: flex;
  gap: 4px;
  align-items: center;
  cursor: pointer;
}
.legend .legend-item .legend-box {
  display: inline-block;
  background-color: #f5f5f5;
  border: 3px solid black;
  width: 40px;
  height: 16px;
}
.legend .legend-item .legend-label {
  font-size: 14px;
  font-weight: normal;
  margin-bottom: 0px;
  cursor: pointer;
}
</style>
