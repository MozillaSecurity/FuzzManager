<template>
  <div class="table">
    <div class="tr">
      <label class="td" for="provider">Bug provider</label>
      <select class="td" name="provider" v-model="selectedProvider">
        <option v-for="p in providers" :key="p.id" :value="p.id">
          {{ p.hostname }}
        </option>
      </select>
    </div>
    <div class="tr">
      <label class="td" for="bug_id">Bug ID</label>
      <input name="bug_id" v-model="externalBugId" maxlength="255" />
    </div>
  </div>
</template>

<script>
export default {
  data: () => ({
    externalBugId: null,
    selectedProvider: null,
  }),
  props: {
    providers: {
      type: Array,
      default: null,
    },
  },
  mounted() {
    this.selectedProvider = this.providers[0].id;
  },
};
</script>

<style scoped>
.table {
  display: table;
}
.tr {
  display: table-row;
  text-align: left;
}
.td {
  display: table-cell;
  padding: 8px;
}
</style>
