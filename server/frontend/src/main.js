import Vue from "vue";
import VueRouter from "vue-router";

import router from "./router.js";
import ActivityGraph from "./components/ActivityGraph.vue";
import AssignBtn from "./components/Buckets/AssignBtn.vue";
import BugPublicationForm from "./components/Bugs/PublicationForm.vue";
import CommentPublicationForm from "./components/Bugs/Comments/PublicationForm.vue";
import ReportsList from "./components/Reports/List.vue";
import ReportStats from "./components/ReportStats.vue";
import ReportStatsGraph from "./components/ReportStatsGraph.vue";
import CreateOrEdit from "./components/Buckets/CreateOrEdit.vue";
import FullPPCSelect from "./components/Bugs/FullPPCSelect.vue";
import Inbox from "./components/Notifications/Inbox.vue";
import ProviderKey from "./components/ProviderKey.vue";
import BucketView from "./components/Buckets/View.vue";
import BucketList from "./components/Buckets/List.vue";

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
      reportslist: ReportsList,
      reportstats: ReportStats,
      reportstatsgraph: ReportStatsGraph,
      createoredit: CreateOrEdit,
      inbox: Inbox,
      ppcselect: FullPPCSelect,
      providerkey: ProviderKey,
      bucketlist: BucketList,
      bucketview: BucketView,
    },
    router,
  });
});
