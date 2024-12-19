<template>
  <div>
    <div
      v-if="assignError"
      class="alert alert-danger alert-message"
      role="alert"
    >
      <button
        type="button"
        class="close"
        data-dismiss="alert"
        aria-label="Close"
        @click="assignError = null"
      >
        <span aria-hidden="true">&times;</span>
      </button>
      An error occurred while assigning this external bug to the current crash
      bucket: {{ assignError }}
    </div>
    <p
      v-if="!duplicates.length"
      class="alert alert-info alert-message"
      role="alert"
    >
      No similar bugs were found.
    </p>
    <div v-else class="pre-scrollable scroll-panel">
      <table class="table table-condensed table-hover table-bordered no-margin">
        <thead>
          <tr>
            <th>ID</th>
            <th>Summary</th>
            <th>Component</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <Row
            v-for="duplicate in duplicates"
            :key="duplicate.id"
            :bug="duplicate"
            :bucket-id="bucketId"
            :provider-id="providerId"
            @error="setAssignError"
          />
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref } from "vue";
import Row from "./Row.vue";

export default defineComponent({
  name: "PossibleDuplicatesList",
  components: {
    Row,
  },
  props: {
    duplicates: {
      type: Array,
      required: true,
    },
    bucketId: {
      type: Number,
      required: true,
    },
    providerId: {
      type: Number,
      required: true,
    },
    providerHostname: {
      type: String,
      required: true,
    },
  },
  setup() {
    const assignError = ref(null);

    const setAssignError = (value) => {
      assignError.value = value;
    };

    return {
      assignError,
      setAssignError,
    };
  },
});
</script>

<style scoped>
.scroll-panel {
  margin-top: 1rem;
  border: 1px solid lightgray;
}
.no-margin {
  margin: 0rem;
}
.alert-message {
  margin-top: 1rem;
  margin-bottom: 0rem;
}
</style>
