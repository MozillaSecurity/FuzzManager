<template>
  <div class="row">
    <div class="form-group col-md-4">
      <label for="bp_select">Provider</label>
      <select id="bp_select" v-model="selectedProvider" class="form-control">
        <option v-for="p in providers" :key="p.id" :value="p.id">
          {{ p.hostname }}
        </option>
      </select>
    </div>

    <ProductComponentSelect
      :provider-hostname="providerHostname"
      :template-product="templateProduct"
      :template-component="templateComponent"
      style-class="col-md-4"
    />
  </div>
</template>

<script>
import { defineComponent, onMounted, ref, watch } from "vue";
import * as api from "../../api";
import ProductComponentSelect from "./ProductComponentSelect.vue";

export default defineComponent({
  name: "FullPPCSelect",
  components: {
    ProductComponentSelect,
  },
  props: {
    providerId: {
      type: Number,
      required: false,
      default: null,
    },
    templateProduct: {
      type: String,
      required: false,
      default: "",
    },
    templateComponent: {
      type: String,
      required: false,
      default: "",
    },
  },
  setup(props) {
    const providers = ref([]);
    const selectedProvider = ref(null);
    const providerHostname = ref("");
    const provider = ref(null);

    onMounted(async () => {
      const data = await api.listBugProviders();
      providers.value = data.results.filter(
        (p) => p.classname === "BugzillaProvider",
      );

      if (props.providerId) {
        provider.value = providers.value.find((p) => p.id === props.providerId);
        selectedProvider.value = provider.value.id;
        providerHostname.value = provider.value.hostname;
      }
    });

    watch(selectedProvider, () => {
      provider.value = providers.value.find(
        (p) => p.id === selectedProvider.value,
      );
      providerHostname.value = provider.value.hostname;
    });

    return {
      providers,
      selectedProvider,
      providerHostname,
      provider,
    };
  },
});
</script>

<style scoped></style>
