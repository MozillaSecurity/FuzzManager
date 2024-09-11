<template>
  <table>
    <tr>
      <th>Tool</th>
      <th>Reports Affected</th>
    </tr>
    <tr v-for="tool in tools" :key="tool">
      <td>{{ tool }}</td>
      <td>{{ toolReports[tool] }}</td>
    </tr>
  </table>
</template>

<script>
export default {
  props: {
    toolReports: {
      type: Object,
      required: true,
    },
  },
  computed: {
    tools() {
      return Object.keys(this.toolReports).sort();
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
