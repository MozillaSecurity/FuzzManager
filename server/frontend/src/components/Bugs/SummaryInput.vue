<template>
  <div class="core">
    <div class="form-group">
      <label for="summary">Summary</label>
      <div class="input-group">
        <input
          id="id_summary"
          class="form-control"
          maxlength="1023"
          name="summary"
          type="text"
          v-model="summary"
        />
        <span class="input-group-btn">
          <button
            class="btn btn-warning"
            type="button"
            :disabled="!summary || loading"
            v-on:click="fetchDuplicates"
          >
            {{ !loading ? "Fetch similar bugs" : "Fetching bugs..." }}
          </button>
        </span>
      </div>
    </div>
    <div v-if="duplicates">
      <div
        v-if="!bugzillaToken"
        class="alert alert-warning alert-message"
        role="alert"
      >
        Similar bugs were retrieved from
        <strong>{{ provider.hostname }}</strong> without any authentication.
        Please define an API Token for this provider in your settings to
        retrieve security bugs.
      </div>
      <List
        :duplicates="duplicates"
        :bucket-id="bucketId"
        :provider-id="provider.id"
        :provider-hostname="provider.hostname"
      />
    </div>
    <div
      v-if="fetchError"
      class="alert alert-danger alert-message"
      role="alert"
    >
      An error occurred while fetching similar bugs from
      <strong>{{ provider.hostname }}</strong
      >.
    </div>
  </div>
</template>

<script>
import * as bugzillaApi from "../../bugzilla_api";
import List from "./PossibleDuplicates/List.vue";

export default {
  components: {
    List,
  },
  props: {
    initialSummary: {
      type: String,
      required: true,
    },
    bucketId: {
      type: Number,
      required: true,
    },
    provider: {
      type: Object,
      required: true,
    },
  },
  data: () => ({
    summary: "",
    loading: false,
    duplicates: null,
    fetchError: false,
  }),
  mounted() {
    this.summary = this.initialSummary;
  },
  computed: {
    bugzillaToken() {
      return localStorage.getItem("provider-" + this.provider.id + "-api-key");
    },
  },
  methods: {
    async fetchDuplicates() {
      this.fetchError = false;
      this.duplicates = null;
      this.loading = true;
      try {
        const data = await bugzillaApi.fetchPossibleDuplicates({
          hostname: this.provider.hostname,
          params: { summary: this.summary },
          headers: this.bugzillaToken
            ? { "X-BUGZILLA-API-KEY": this.bugzillaToken }
            : {},
        });
        this.duplicates = data.bugs.map((b) => {
          return { ...b, link: `https://${this.provider.hostname}/${b.id}` };
        });
      } catch {
        this.fetchError = true;
      } finally {
        this.loading = false;
      }
    },
  },
  watch: {
    provider: function () {
      this.loading = false;
      this.duplicates = null;
      this.fetchError = false;
    },
    initialSummary: function () {
      this.summary = this.initialSummary;
    },
    summary: function () {
      this.$emit("update-summary", this.summary);
    },
  },
};
</script>

<style scoped>
.alert-message {
  margin-top: 1rem;
  margin-bottom: 0rem;
}
.core {
  margin-bottom: 1.5rem;
}
</style>
