<template>
  <div class="row">
    <div class="form-group col-md-4">
      <label for="bp_select">Provider</label>
      <select id="bp_select" class="form-control" v-model="selectedProvider">
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
import * as api from "../../api";
import ProductComponentSelect from "./ProductComponentSelect.vue";

export default {
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
  data: () => ({
    providers: [],
    selectedProvider: null,
    providerHostname: "",
    provider: null,
  }),
  async mounted() {
    let data = await api.listBugProviders();
    this.providers = data.results.filter(
      (p) => p.classname === "BugzillaProvider"
    );
    if (this.providerId) {
      this.provider = this.providers.find((p) => p.id === this.providerId);
      this.selectedProvider = this.provider.id;
      this.providerHostname = this.provider.hostname;
    }
  },
  watch: {
    selectedProvider() {
      this.provider = this.providers.find(
        (p) => p.id === this.selectedProvider
      );
      this.providerHostname = this.provider.hostname;
    },
  },
};
</script>

<style scoped></style>
