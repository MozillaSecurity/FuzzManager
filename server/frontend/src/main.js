import _ from "lodash"; // eslint-disable-line no-unused-vars
import sweetAlert from "sweetalert"; // eslint-disable-line no-unused-vars

import Vue from "vue";
import VueRouter from "vue-router";
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

Vue.use(VueRouter);

window.onload = function () {
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
};
