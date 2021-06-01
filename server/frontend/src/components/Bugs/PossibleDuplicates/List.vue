<template>
  <div>
    <button
      type="button"
      class="btn btn-warning"
      :disabled="!summary || loading"
      v-on:click="fetchDuplicates"
    >
      {{ !loading ? "Fetch similar bugs" : "Fetching bugs..." }}
    </button>

    <div
      v-if="duplicates && !bugzillaToken"
      class="alert alert-warning alert-message"
      role="alert"
    >
      Similar bugs were retrieved from
      <strong>{{ providerHostname }}</strong> without any authentication. Please
      define an API Token for this provider in your settings to retrieve
      security bugs.
    </div>

    <p v-if="duplicates && !duplicates.length">No similar bugs were found.</p>
    <div
      class="pre-scrollable scroll-panel"
      v-if="duplicates && duplicates.length"
    >
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
            :entry-id="entryId"
            :provider-id="providerId"
          />
        </tbody>
      </table>
    </div>

    <div
      v-if="fetchError"
      class="alert alert-danger alert-message"
      role="alert"
    >
      An error occured while fetching similar bugs from
      <strong>{{ providerHostname }}</strong
      >.
    </div>
  </div>
</template>

<script>
import * as bugzillaApi from "../../../bugzilla_api";
import Row from "./Row.vue";

export default {
  components: {
    Row,
  },
  props: {
    summary: {
      type: String,
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
    providerHostname: {
      type: String,
      required: true,
    },
  },
  data: () => ({
    loading: false,
    duplicates: null,
    fetchError: false,
  }),
  computed: {
    bugzillaToken() {
      return localStorage.getItem("provider-" + this.providerId + "-api-key");
    },
  },
  methods: {
    async fetchDuplicates() {
      this.fetchError = false;
      this.duplicates = null;
      this.loading = true;
      try {
        const data = await bugzillaApi.fetchPossibleDuplicates({
          hostname: this.providerHostname,
          params: { summary: this.summary },
          headers: this.bugzillaToken
            ? { "X-BUGZILLA-API-KEY": this.bugzillaToken }
            : {},
        });
        this.duplicates = data.bugs.map((b) => {
          return { ...b, link: `https://${this.providerHostname}/${b.id}` };
        });
      } catch {
        this.fetchError = true;
      } finally {
        this.loading = false;
      }
    },
  },
};
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
