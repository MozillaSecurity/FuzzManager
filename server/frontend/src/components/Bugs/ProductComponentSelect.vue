<template>
  <div>
    <div>
      <div class="form-group" :class="styleClass" v-if="!fetchError">
        <label for="product">Product*</label>
        <div class="input-group">
          <span class="input-group-btn">
            <button
              type="button"
              class="btn btn-secondary"
              :disabled="!providerHostname"
              title="Refresh product list"
              v-on:click="refreshProducts"
            >
              <i class="bi bi-repeat"></i>
            </button>
          </span>
          <select
            id="product"
            name="product"
            class="form-control"
            v-model="selectedProduct"
            :disabled="!providerHostname"
          >
            <option
              v-if="providerHostname && !products.length"
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
      <div class="form-group" :class="styleClass" v-else>
        <label for="product">Product*</label>
        <input
          type="text"
          id="product"
          name="product"
          class="form-control"
          :value="templateProduct"
        />
      </div>
      <div class="form-group" :class="styleClass" v-if="!fetchError">
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
      <div class="form-group" :class="styleClass" v-else>
        <label for="component">Component*</label>
        <input
          type="text"
          id="component"
          name="component"
          class="form-control"
          :value="templateComponent"
        />
      </div>
    </div>

    <div class="row override-row">
      <div
        v-if="fetchError"
        class="alert alert-danger error-message col-md-12"
        role="alert"
      >
        An error occurred while fetching products and components from
        <strong>{{ providerHostname }}</strong
        >. Please, enter your product and component by hand.
      </div>
    </div>
  </div>
</template>

<script>
import * as bugzillaApi from "../../bugzilla_api";

export default {
  props: {
    providerHostname: {
      type: String,
      required: true,
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
    styleClass: {
      type: String,
      required: false,
      default: "col-md-6",
    },
  },
  data: () => ({
    fetchError: false,
    products: [],
    selectedProduct: "",
    selectedComponent: "",
  }),
  async mounted() {
    this.assignProducts();
  },
  computed: {
    localStorageKey() {
      if (!this.providerHostname) return null;
      return "bugzilla-products-" + this.providerHostname;
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

      if (this.products && this.products.length && this.templateProduct) {
        const product = this.products.find(
          (p) => p.name === this.templateProduct
        );
        if (product) {
          this.selectedProduct = product.name;
          if (this.templateComponent) {
            const component = product.components.find(
              (c) => c === this.templateComponent
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
       * Return fetched products and components retrieved from https://{providerHostname}/latest/configuration
       * Also store them in browser localStorage under "bugzilla-products-{providerHostname}" key
       */
      try {
        const data = await bugzillaApi.fetchLatestConfiguration(
          this.providerHostname
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
    providerHostname: function () {
      this.fetchError = false;
      this.products = [];
      this.selectedProduct = "";
      this.selectedComponent = "";
      this.assignProducts();
    },
    templateProduct: function (newVal, oldVal) {
      if (newVal !== oldVal) {
        this.selectedProduct = "";
        this.assignProducts();
      }
    },
    templateComponent: function (newVal, oldVal) {
      if (newVal !== oldVal) {
        this.selectedComponent = "";
        this.assignProducts();
      }
    },
    selectedProduct: function () {
      this.$emit("update-product", this.selectedProduct);
    },
    selectedComponent: function () {
      this.$emit("update-component", this.selectedComponent);
    },
  },
};
</script>

<style scoped>
.override-row {
  margin-left: 1.5rem;
  margin-right: 1.5rem;
}
.error-message {
  margin-top: 0rem;
  margin-bottom: 1.5rem;
}
</style>
