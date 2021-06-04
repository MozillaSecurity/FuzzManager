import _ from "lodash"; // eslint-disable-line no-unused-vars
import sweetAlert from "sweetalert"; // eslint-disable-line no-unused-vars
import { E_SERVER_ERROR, formatClientTimestamp } from "./helpers";
window.E_SERVER_ERROR = E_SERVER_ERROR;
window.formatClientTimestamp = formatClientTimestamp;

import Vue from "vue";
import VueRouter from "vue-router";
import router from "./router.js";
import CrashesList from "./components/Crashes/List.vue";
import CreateOrEdit from "./components/Signatures/CreateOrEdit.vue";
import ProviderKey from "./components/ProviderKey.vue";
import ProductComponentSelect from "./components/Bugs/ProductComponentSelect.vue";
import SummaryInput from "./components/Bugs/SummaryInput.vue";

Vue.use(VueRouter);

window.onload = function () {
  new Vue({
    el: "#app",
    components: {
      createoredit: CreateOrEdit,
      crasheslist: CrashesList,
      providerkey: ProviderKey,
      productcomponentselect: ProductComponentSelect,
      summaryinput: SummaryInput,
    },
    router,
  });
};
