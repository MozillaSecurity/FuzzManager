<template>
  <table>
    <tr>
      <th>Reports Affected</th>
    </tr>
    <tr>
      <td>{{ reportCount }}</td>
    </tr>
  </table>
</template>

<script>
export default {
  props: {
    reportCount: {
      type: Number,
      required: true,
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
