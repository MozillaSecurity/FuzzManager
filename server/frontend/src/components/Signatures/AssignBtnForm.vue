<template>
  <div class="table">
    <div class="tr">
      <label class="td" for="provider">Bug provider</label>
      <select
        v-model="selectedProvider"
        class="td"
        name="provider"
        @change="$emit('update-provider', selectedProvider)"
      >
        <option v-for="p in providers" :key="p.id" :value="p.id">
          {{ p.hostname }}
        </option>
      </select>
    </div>
    <div class="tr">
      <label class="td" for="bug_id">Bug ID</label>
      <input
        v-model="externalBugId"
        maxlength="255"
        name="bug_id"
        @change="$emit('update-bug', externalBugId)"
      />
    </div>
  </div>
</template>

<script>
import { defineComponent, onMounted, ref } from "vue";

export default defineComponent({
  props: {
    providers: {
      type: Array,
      default: () => [],
    },
  },

  setup(props, context) {
    const externalBugId = ref(null);
    const selectedProvider = ref(null);

    onMounted(() => {
      if (props.providers.length > 0) {
        selectedProvider.value = props.providers[0].id;
        context.emit("update-provider", selectedProvider.value);
      }
    });

    return {
      externalBugId,
      selectedProvider,
    };
  },
});
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
