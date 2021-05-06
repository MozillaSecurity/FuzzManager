import _ from "lodash"; // eslint-disable-line no-unused-vars
import sweetAlert from "sweetalert"; // eslint-disable-line no-unused-vars
import { E_SERVER_ERROR, formatClientTimestamp } from "./helpers";
window.E_SERVER_ERROR = E_SERVER_ERROR;
window.formatClientTimestamp = formatClientTimestamp;

import Vue from "vue";
import List from "./components/Crashes/List.vue";
import CreateOrEdit from "./components/Signatures/CreateOrEdit.vue";

window.onload = function () {
  new Vue({
    el: "#app",
    components: {
      createoredit: CreateOrEdit,
      crasheslist: List,
    },
  });
};
