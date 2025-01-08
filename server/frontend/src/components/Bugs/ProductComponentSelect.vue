<template>
  <div>
    <div>
      <div v-if="!fetchError" class="form-group" :class="styleClass">
        <label for="product">Product*</label>
        <div class="input-group">
          <span class="input-group-btn">
            <button
              type="button"
              class="btn btn-secondary"
              :disabled="!providerHostname"
              title="Refresh product list"
              @click="refreshProducts"
            >
              <i class="bi bi-repeat"></i>
            </button>
          </span>
          <select
            id="product"
            v-model="selectedProduct"
            name="product"
            class="form-control"
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
      <div v-else class="form-group" :class="styleClass">
        <label for="product">Product*</label>
        <input
          id="product"
          type="text"
          name="product"
          class="form-control"
          :value="templateProduct"
        />
      </div>
      <div v-if="!fetchError" class="form-group" :class="styleClass">
        <label for="component">Component*</label>
        <select
          id="component"
          v-model="selectedComponent"
          name="component"
          class="form-control"
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
      <div v-else class="form-group" :class="styleClass">
        <label for="component">Component*</label>
        <input
          id="component"
          type="text"
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
import { computed, defineComponent, onMounted, ref, watch } from "vue";
import * as bugzillaApi from "../../bugzilla_api";

export default defineComponent({
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

  setup(props, { emit }) {
    const fetchError = ref(false);
    const products = ref([]);
    const selectedProduct = ref("");
    const selectedComponent = ref("");

    const localStorageKey = computed(() => {
      if (!props.providerHostname) return null;
      return "bugzilla-products-" + props.providerHostname;
    });

    const components = computed(() => {
      if (!products.value || !selectedProduct.value) return [];
      return (
        products.value.find((p) => p.name === selectedProduct.value)
          ?.components || []
      );
    });

    const fetchProducts = async () => {
      /*
       * Return fetched products and components retrieved from https://{providerHostname}/latest/configuration
       * Also store them in browser localStorage under "bugzilla-products-{providerHostname}" key
       */
      try {
        const data = await bugzillaApi.fetchLatestConfiguration(
          props.providerHostname,
        );
        const productsList = Object.entries(data.product)
          .filter(([, product]) => product.is_active)
          .map(([name, product]) => ({
            id: product.id,
            name: name,
            components: Object.entries(product.component)
              .filter(([, component]) => component.is_active)
              .map(([name]) => name),
          }));

        const toSave = {
          version: data.version,
          stored: new Date(),
          products: productsList,
        };
        localStorage.setItem(localStorageKey.value, JSON.stringify(toSave));
        return toSave;
      } catch {
        fetchError.value = true;
        return [];
      }
    };

    const assignProducts = async () => {
      if (!localStorageKey.value) {
        products.value = [];
        return;
      }

      let stored = JSON.parse(localStorage.getItem(localStorageKey.value));
      const lastWeek = new Date().setDate(new Date().getDate() - 7);

      if (!stored || new Date(stored.stored).getTime() < lastWeek) {
        stored = await fetchProducts();
      }
      products.value = stored.products;

      if (products.value?.length && props.templateProduct) {
        const product = products.value.find(
          (p) => p.name === props.templateProduct,
        );
        if (product) {
          selectedProduct.value = product.name;
          if (props.templateComponent) {
            const component = product.components.find(
              (c) => c === props.templateComponent,
            );
            if (component) selectedComponent.value = component;
          }
        }
      }
    };

    const refreshProducts = async () => {
      localStorage.removeItem(localStorageKey.value);
      products.value = [];
      selectedProduct.value = "";
      selectedComponent.value = "";
      await assignProducts();
    };

    // Watchers
    watch(
      () => props.providerHostname,
      () => {
        fetchError.value = false;
        products.value = [];
        selectedProduct.value = "";
        selectedComponent.value = "";
        assignProducts();
      },
    );

    watch(
      () => props.templateProduct,
      (newVal, oldVal) => {
        if (newVal !== oldVal) {
          selectedProduct.value = "";
          assignProducts();
        }
      },
    );

    watch(
      () => props.templateComponent,
      (newVal, oldVal) => {
        if (newVal !== oldVal) {
          selectedComponent.value = "";
          assignProducts();
        }
      },
    );

    watch(
      () => selectedProduct.value,
      () => {
        emit("update-product", selectedProduct.value);
      },
    );

    watch(
      () => selectedComponent.value,
      () => {
        emit("update-component", selectedComponent.value);
      },
    );

    onMounted(() => {
      assignProducts();
    });

    return {
      fetchError,
      products,
      selectedProduct,
      selectedComponent,
      components,
      localStorageKey,
      refreshProducts,
    };
  },
});
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
