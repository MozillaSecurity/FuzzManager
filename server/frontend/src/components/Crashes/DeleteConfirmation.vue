<template>
  <table>
    <tr>
      <th>Tool</th>
      <th>Crashes Affected</th>
    </tr>
    <tr v-for="tool in tools" :key="tool">
      <td>{{ tool }}</td>
      <td>{{ toolCrashes[tool] }}</td>
    </tr>
  </table>
</template>

<script>
export default {
  props: {
    toolCrashes: {
      type: Object,
      required: true,
    },
  },
  computed: {
    tools() {
      const result = Object.keys(this.toolCrashes);
      result.sort();
      return result;
    },
  },
};
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
