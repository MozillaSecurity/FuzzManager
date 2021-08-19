import Vue from "vue";
import VueRouter from "vue-router";
import { BootstrapVue } from "bootstrap-vue";

import router from "./router.js";
import BugPublicationForm from "./components/Bugs/PublicationForm.vue";
import CommentPublicationForm from "./components/Bugs/Comments/PublicationForm.vue";
import CrashesList from "./components/Crashes/List.vue";
import CreateOrEdit from "./components/Signatures/CreateOrEdit.vue";
import FullPPCSelect from "./components/Bugs/FullPPCSelect.vue";
import Inbox from "./components/Notifications/Inbox.vue";
import PoolView from "./components/Pools/View.vue";
import PoolsList from "./components/Pools/List.vue";
import ProviderKey from "./components/ProviderKey.vue";
import SignaturesList from "./components/Signatures/List.vue";

import "sweetalert/dist/sweetalert.css";

Vue.use(VueRouter);
Vue.use(BootstrapVue);

document.addEventListener("DOMContentLoaded", function () {
  new Vue({
    el: "#app",
    components: {
      bugpublicationform: BugPublicationForm,
      commentpublicationform: CommentPublicationForm,
      crasheslist: CrashesList,
      createoredit: CreateOrEdit,
      inbox: Inbox,
      poolslist: PoolsList,
      poolview: PoolView,
      ppcselect: FullPPCSelect,
      providerkey: ProviderKey,
      signatureslist: SignaturesList,
    },
    router,
  });
});
