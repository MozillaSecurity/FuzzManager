<template>
  <table>
    <thead>
      <tr>
        <th>Tool</th>
        <th>Crashes Affected</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="tool in tools" :key="tool">
        <td>{{ tool }}</td>
        <td>{{ toolCrashes[tool] }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script>
import { computed, defineComponent } from "vue";

export default defineComponent({
  props: {
    toolCrashes: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const tools = computed(() => Object.keys(props.toolCrashes).sort());
    return {
      tools,
    };
  },
});
</script>

<style scoped>
table {
  margin: 0 auto;
}
th,
td {
  padding: 8px;
}
</style>
