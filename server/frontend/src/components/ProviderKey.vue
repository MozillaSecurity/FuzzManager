<template>
  <div class="mt-strong">
    <strong>{{ providerHostname }}:</strong>
    <div class="form-inline mt-light">
      <div class="input-group">
        <input
          v-model="key"
          type="text"
          class="form-control"
          placeholder="API key..."
        />
        <span class="input-group-btn">
          <button
            type="button"
            class="btn btn-success"
            :disabled="loading"
            @click="saveKey"
          >
            {{ !loading ? "Save" : "Saving..." }}
          </button>
        </span>
      </div>
      <button
        type="button"
        class="btn btn-danger"
        title="Remove key"
        @click="removeKey"
      >
        <span class="bi bi-trash-fill" aria-hidden="true"></span>
      </button>
      <br />
      <div
        v-if="success"
        class="alert alert-success alert-dismissible mt-strong"
        role="alert"
      >
        <button
          type="button"
          class="close"
          data-dismiss="alert"
          aria-label="Close"
          @click="success = null"
        >
          <span aria-hidden="true">&times;</span>
        </button>
        Welcome <strong>{{ bugzillaUsername }}</strong
        >! Your API key for <strong>{{ providerHostname }}</strong> provider was
        correctly saved.
      </div>
      <div
        v-if="error"
        class="alert alert-danger alert-dismissible mt-strong"
        role="alert"
      >
        <button
          type="button"
          class="close"
          data-dismiss="alert"
          aria-label="Close"
          @click="error = null"
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
import { computed, defineComponent, onMounted, ref } from "vue";
import * as bugzillaApi from "../bugzilla_api";
import { errorParser } from "../helpers";

export default defineComponent({
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
  setup(props) {
    const key = ref(null);
    const loading = ref(false);
    const error = ref(null);
    const success = ref(null);

    const localStorageKey = computed(
      () => "provider-" + props.providerId + "-api-key",
    );

    const bugzillaUsername = computed(
      () => success.value?.real_name || success.value?.nick,
    );

    const saveKey = async () => {
      loading.value = true;
      success.value = null;
      error.value = null;

      try {
        const data = await bugzillaApi.whoAmI({
          hostname: props.providerHostname,
          key: key.value,
        });
        localStorage.setItem(localStorageKey.value, key.value);
        success.value = data;
      } catch (err) {
        if (err.response?.data?.message) {
          error.value = err.response.data.message;
        } else {
          error.value = errorParser(err);
        }
      } finally {
        loading.value = false;
      }
    };

    const removeKey = () => {
      success.value = null;
      error.value = null;
      localStorage.removeItem(localStorageKey.value);
      key.value = null;
    };

    onMounted(() => {
      const storedKey = localStorage.getItem(localStorageKey.value);

      if (storedKey) key.value = storedKey;
    });

    return {
      key,
      loading,
      error,
      success,
      bugzillaUsername,
      localStorageKey,
      saveKey,
      removeKey,
    };
  },
});
</script>

<style scoped>
.mt-strong {
  margin-top: 1.5rem;
}
.mt-light {
  margin-top: 0.5rem;
}
.btn {
  margin-left: 0.8rem;
}
</style>
