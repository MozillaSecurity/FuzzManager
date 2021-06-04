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
import { errorParser } from "../../../helpers";
import * as api from "../../../api";

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
    async assignExternalBug() {
      this.$emit("error", null);
      const payload = {
        bug: this.bug.id,
        provider: this.providerId,
      };

      try {
        const data = await api.updateBucket({
          id: this.bucketId,
          params: { reassign: false },
          ...payload,
        });
        window.location.href = data.url;
      } catch (err) {
        this.$emit("error", errorParser(err));
      }
    },
  },
};
</script>

<style scoped></style>
