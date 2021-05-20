<template>
  <div class="mt-strong">
    <strong>{{ providerHostname }}:</strong>
    <div class="form-inline mt-light">
      <div class="input-group">
        <input
          type="text"
          class="form-control"
          placeholder="API key..."
          v-model="key"
        />
        <span class="input-group-btn">
          <button type="button" class="btn btn-success" v-on:click="saveKey">
            Save
          </button>
        </span>
      </div>
      <button
        type="button"
        class="btn btn-danger"
        v-on:click="removeKey"
        title="Remove key"
      >
        <span class="glyphicon glyphicon-trash" aria-hidden="true"></span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    providerId: {
      type: Number,
      required: true,
    },
    providerHostname: {
      type: String,
      required: true,
    },
  },
  data: () => ({
    key: null,
  }),
  mounted() {
    const storedKey = localStorage.getItem(this.localStorageKey);
    if (storedKey) this.key = storedKey;
  },
  computed: {
    localStorageKey() {
      return "provider-" + this.providerId;
    },
  },
  methods: {
    saveKey() {
      localStorage.setItem(this.localStorageKey, this.key);
    },
    removeKey() {
      localStorage.removeItem(this.localStorageKey);
      this.key = null;
    },
  },
};
</script>

<style scoped>
.mt-strong {
  margin-top: 1.5rem;
}
.mt-light {
  margin-top: 0.5rem;
}
</style>
