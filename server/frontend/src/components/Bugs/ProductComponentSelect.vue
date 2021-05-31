<template>
  <div class="row">
    <div class="col-md-4">
      <label for="bp_select">Provider</label>
      <select id="bp_select" class="form-control" v-model="selectedProvider">
        <option
          v-for="provider in providers"
          :key="provider.hostname"
          :value="provider.hostname"
        >
          {{ provider.hostname }}
        </option>
      </select>
    </div>
    <div class="col-md-4">
      <label for="product">Product</label>
      <div class="row">
        <div class="col-md-2">
          <button
            type="button"
            class="btn btn-secondary"
            :disabled="!selectedProvider"
            title="Refresh product list"
            v-on:click="refreshProducts"
          >
            <i class="glyphicon glyphicon-refresh"></i>
          </button>
        </div>
        <div class="col-md-10">
          <select
            id="product"
            name="product"
            class="form-control"
            v-model="selectedProduct"
            :disabled="!selectedProvider"
          >
            <option
              v-if="selectedProvider && !products.length"
              value=""
              disabled
            >
              Products loading...
            </option>
            <option
              v-for="product in products"
              :key="product.id"
              :value="product.name"
            >
              {{ product.name }}
            </option>
          </select>
        </div>
      </div>
    </div>
    <div class="col-md-4">
      <label for="component">Component</label>
      <select
        id="component"
        name="component"
        class="form-control"
        v-model="selectedComponent"
        :disabled="!selectedProduct"
      >
        <option
          v-for="component in components"
          :key="component"
          :value="component"
        >
          {{ component }}
        </option>
      </select>
    </div>
  </div>
</template>

<script>
import * as api from "../../api";
import * as bugzillaApi from "../../bugzilla_api";

export default {
  data: () => ({
    providers: [],
    selectedProvider: null,
    products: [],
    selectedProduct: "",
    selectedComponent: "",
  }),
  async mounted() {
    const data = await api.listBugProviders();
    this.providers = data.results.filter(
      (p) => p.classname === "BugzillaProvider"
    );
    this.assignProducts();
  },
  computed: {
    localStorageKey() {
      if (!this.selectedProvider) return null;
      return "bugzilla-products-" + this.selectedProvider;
    },
    components() {
      if (!this.products || !this.selectedProduct) return [];
      return this.products.find((p) => p.name === this.selectedProduct)
        .components;
    },
  },
  methods: {
    async assignProducts() {
      if (!this.localStorageKey) {
        this.products = [];
      } else {
        let stored = JSON.parse(localStorage.getItem(this.localStorageKey));
        if (!stored) stored = await this.fetchProducts();
        this.products = stored.products;
      }
    },
    async refreshProducts() {
      localStorage.removeItem(this.localStorageKey);
      this.products = [];
      this.selectedProduct = "";
      this.selectedComponent = "";
      this.assignProducts();
    },
    async fetchProducts() {
      const data = await bugzillaApi.fetchLatestConfiguration(
        this.selectedProvider
      );
      const products = Object.entries(data.product)
        .filter(([, product]) => product.is_active)
        .map(([name, product]) => {
          return {
            id: product.id,
            name: name,
            components: Object.entries(product.component)
              .filter(([, component]) => component.is_active)
              .map(([name]) => name),
          };
        });
      const toSave = { version: data.version, products: products };
      localStorage.setItem(this.localStorageKey, JSON.stringify(toSave));
      return toSave;
    },
  },
  watch: {
    selectedProvider: function () {
      this.products = [];
      this.selectedProduct = "";
      this.selectedComponent = "";
      this.assignProducts();
    },
  },
};
</script>

<style scoped></style>
