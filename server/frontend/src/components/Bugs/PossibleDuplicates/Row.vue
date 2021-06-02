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
    entryId: {
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
        bug_id: this.bug.id,
        provider: this.providerId,
      };

      try {
        const data = await api.assignExternalBug({
          id: this.entryId,
          ...payload,
        });
        window.location.href = data.redirect_url;
      } catch (err) {
        this.$emit("error", errorParser(err));
      }
    },
  },
};
</script>

<style scoped></style>
