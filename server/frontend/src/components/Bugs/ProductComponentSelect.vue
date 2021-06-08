<template>
  <div>
    <div class="row">
      <div class="form-group col-md-4">
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
      <div class="form-group col-md-4" v-if="!fetchError">
        <label for="product">Product*</label>
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
      <div class="form-group col-md-4" v-else>
        <label for="product">Product*</label>
        <input
          type="text"
          id="product"
          name="product"
          class="form-control"
          :value="defaultTemplateProduct"
        />
      </div>
      <div class="form-group col-md-4" v-if="!fetchError">
        <label for="component">Component*</label>
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
      <div class="form-group col-md-4" v-else>
        <label for="component">Component*</label>
        <input
          type="text"
          id="component"
          name="component"
          class="form-control"
          :value="defaultTemplateComponent"
        />
      </div>
    </div>

    <div
      v-if="fetchError"
      class="alert alert-danger error-message"
      role="alert"
    >
      An error occurred while fetching products and components from
      <strong>{{ selectedProvider }}</strong
      >. Please, enter your product and component by hand.
    </div>
  </div>
</template>

<script>
import * as api from "../../api";
import * as bugzillaApi from "../../bugzilla_api";

export default {
  props: {
    defaultProvider: {
      type: String,
      required: false,
      default: null,
    },
    defaultTemplateProduct: {
      type: String,
      required: false,
      default: "",
    },
    defaultTemplateComponent: {
      type: String,
      required: false,
      default: "",
    },
  },
  data: () => ({
    fetchError: false,
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
    if (this.defaultProvider) this.selectedProvider = this.defaultProvider;
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
        const lastWeek = new Date().setDate(new Date().getDate() - 7);
        if (!stored || new Date(stored.stored).getTime() < lastWeek)
          stored = await this.fetchProducts();
        this.products = stored.products;
      }

      if (this.defaultTemplateProduct) {
        const product = this.products.find(
          (p) => p.name === this.defaultTemplateProduct
        );
        if (product) {
          this.selectedProduct = product.name;
          if (this.defaultTemplateComponent) {
            const component = product.components.find(
              (c) => c === this.defaultTemplateComponent
            );
            if (component) this.selectedComponent = component;
          }
        }
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
      /*
       * Return fetched products and components retrieved from https://{selectedProvider}/latest/configuration
       * Also store them in browser localStorage under "bugzilla-products-{selectedProvider}" key
       */
      try {
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
        const toSave = {
          version: data.version,
          stored: new Date(),
          products: products,
        };
        localStorage.setItem(this.localStorageKey, JSON.stringify(toSave));
        return toSave;
      } catch {
        this.fetchError = true;
        return [];
      }
    },
  },
  watch: {
    selectedProvider: function () {
      this.fetchError = false;
      this.products = [];
      this.selectedProduct = "";
      this.selectedComponent = "";
      this.assignProducts();
    },
  },
};
</script>

<style scoped>
.error-message {
  margin-top: 0rem;
  margin-bottom: 1.5rem;
}
</style>
