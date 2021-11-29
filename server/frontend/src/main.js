import Vue from "vue";
import VueRouter from "vue-router";

import router from "./router.js";
import ActivityGraph from "./components/ActivityGraph.vue";
import AssignBtn from "./components/Signatures/AssignBtn.vue";
import BugPublicationForm from "./components/Bugs/PublicationForm.vue";
import CommentPublicationForm from "./components/Bugs/Comments/PublicationForm.vue";
import CrashesList from "./components/Crashes/List.vue";
import CreateOrEdit from "./components/Signatures/CreateOrEdit.vue";
import FullPPCSelect from "./components/Bugs/FullPPCSelect.vue";
import Inbox from "./components/Notifications/Inbox.vue";
import PoolView from "./components/Pools/View.vue";
import PoolsList from "./components/Pools/List.vue";
import ProviderKey from "./components/ProviderKey.vue";
import SignatureView from "./components/Signatures/View.vue";
import SignaturesList from "./components/Signatures/List.vue";

import "vue-popperjs/dist/vue-popper.css";

Vue.use(VueRouter);

document.addEventListener("DOMContentLoaded", function () {
  new Vue({
    el: "#app",
    components: {
      activitygraph: ActivityGraph,
      assignbutton: AssignBtn,
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
      signatureview: SignatureView,
    },
    router,
  });
});
