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
          <button
            type="button"
            class="btn btn-success"
            :disabled="loading"
            v-on:click="saveKey"
          >
            {{ !loading ? "Save" : "Saving..." }}
          </button>
        </span>
      </div>
      <button
        type="button"
        class="btn btn-danger"
        v-on:click="removeKey"
        title="Remove key"
      >
        <span class="bi bi-trash-fill" aria-hidden="true"></span>
      </button>
      <br />
      <div
        class="alert alert-success alert-dismissible mt-strong"
        role="alert"
        v-if="success"
      >
        <button
          type="button"
          class="close"
          data-dismiss="alert"
          aria-label="Close"
          v-on:click="success = null"
        >
          <span aria-hidden="true">&times;</span>
        </button>
        Welcome <strong>{{ bugzillaUsername }}</strong
        >! Your API key for <strong>{{ providerHostname }}</strong> provider was
        correctly saved.
      </div>
      <div
        class="alert alert-danger alert-dismissible mt-strong"
        role="alert"
        v-if="error"
      >
        <button
          type="button"
          class="close"
          data-dismiss="alert"
          aria-label="Close"
          v-on:click="error = null"
        >
          <span aria-hidden="true">&times;</span>
        </button>
        Your API key wasn't saved because an error occurred while contacting
        <strong>{{ providerHostname }}</strong> API:
        <br />
        <em class="mt-light">{{ error }}</em>
      </div>
    </div>
  </div>
</template>

<script>
import { errorParser } from "../helpers";
import * as bugzillaApi from "../bugzilla_api";

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
    loading: false,
    error: null,
    success: null,
  }),
  mounted() {
    const storedKey = localStorage.getItem(this.localStorageKey);
    if (storedKey) this.key = storedKey;
  },
  computed: {
    localStorageKey() {
      return "provider-" + this.providerId + "-api-key";
    },
    bugzillaUsername() {
      return this.success.real_name
        ? this.success.real_name
        : this.success.nick;
    },
  },
  methods: {
    async saveKey() {
      this.loading = true;
      this.success = null;
      this.error = null;

      try {
        const data = await bugzillaApi.whoAmI({
          hostname: this.providerHostname,
          key: this.key,
        });
        localStorage.setItem(this.localStorageKey, this.key);
        this.success = data;
      } catch (err) {
        if (err.response && err.response.data && err.response.data.message) {
          this.error = err.response.data.message;
        } else {
          this.error = errorParser(err);
        }
      } finally {
        this.loading = false;
      }
    },
    removeKey() {
      this.success = null;
      this.error = null;
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
