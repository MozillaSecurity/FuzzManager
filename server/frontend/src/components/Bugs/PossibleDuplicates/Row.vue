<template>
  <tr>
    <td>
      <a :href="bug.link" target="_blank">{{ bug.id }}</a>
    </td>
    <td>{{ bug.summary }}</td>
    <td>{{ bug.component }}</td>
    <td>{{ bug.status }}</td>
    <td>
      <button
        type="button"
        class="btn btn-secondary"
        v-on:click="assignExternalBug"
      >
        Use this bug
      </button>
    </td>
  </tr>
</template>

<script>
import { assignExternalBug, errorParser } from "../../../helpers";

export default {
  props: {
    bug: {
      type: Object,
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
  },
  methods: {
    assignExternalBug() {
      this.$emit("error", null);
      assignExternalBug(this.bucketId, this.bug.id, this.providerId)
        .then((data) => {
          window.location.href = data.url;
        })
        .catch((err) => {
          this.$emit("error", errorParser(err));
        });
    },
  },
};
</script>

<style scoped></style>
