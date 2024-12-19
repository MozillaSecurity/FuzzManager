<template>
  <div class="core">
    <div class="form-group">
      <label for="summary">Summary</label>
      <div class="input-group">
        <input
          id="id_summary"
          v-model="summary"
          class="form-control"
          maxlength="1023"
          name="summary"
          type="text"
        />
        <span class="input-group-btn">
          <button
            class="btn btn-warning"
            type="button"
            :disabled="!summary || loading"
            @click="fetchDuplicates"
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
import { computed, defineComponent, ref, watch } from "vue";
import * as bugzillaApi from "../../bugzilla_api";
import List from "./PossibleDuplicates/List.vue";

export default defineComponent({
  name: "SummaryInput",
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
  setup(props, { emit }) {
    const summary = ref("");
    const loading = ref(false);
    const duplicates = ref(null);
    const fetchError = ref(false);

    // Computed property for bugzilla token
    const bugzillaToken = computed(() => {
      return localStorage.getItem("provider-" + props.provider.id + "-api-key");
    });

    // Methods
    const fetchDuplicates = async () => {
      fetchError.value = false;
      duplicates.value = null;
      loading.value = true;

      try {
        const data = await bugzillaApi.fetchPossibleDuplicates({
          hostname: props.provider.hostname,
          params: { summary: summary.value },
          headers: bugzillaToken.value
            ? { "X-BUGZILLA-API-KEY": bugzillaToken.value }
            : {},
        });
        duplicates.value = data.bugs.map((b) => {
          return { ...b, link: `https://${props.provider.hostname}/${b.id}` };
        });
      } catch {
        fetchError.value = true;
      } finally {
        loading.value = false;
      }
    };

    watch(
      () => props.provider,
      () => {
        loading.value = false;
        duplicates.value = null;
        fetchError.value = false;
      },
    );

    watch(
      () => props.initialSummary,
      () => {
        summary.value = props.initialSummary;
      },
    );

    watch(summary, () => {
      emit("update-summary", summary.value);
    });

    summary.value = props.initialSummary;

    return {
      summary,
      loading,
      duplicates,
      fetchError,
      bugzillaToken,
      fetchDuplicates,
    };
  },
});
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
