import { createApp } from "vue";
import { LoadingPlugin } from "vue-loading-overlay";
import "vue-loading-overlay/dist/css/index.css";

// Components imports
import FloatingVue from "floating-vue";
import "floating-vue/dist/style.css";
import ActivityGraph from "./components/ActivityGraph.vue";
import CommentPublicationForm from "./components/Bugs/Comments/PublicationForm.vue";
import FullPPCSelect from "./components/Bugs/FullPPCSelect.vue";
import BugPublicationForm from "./components/Bugs/PublicationForm.vue";
import CrashesList from "./components/Crashes/List.vue";
import CrashStats from "./components/CrashStats.vue";
import CrashStatsGraph from "./components/CrashStatsGraph.vue";
import Inbox from "./components/Notifications/Inbox.vue";
import PoolsList from "./components/Pools/List.vue";
import PoolView from "./components/Pools/View.vue";
import ProviderKey from "./components/ProviderKey.vue";
import AssignBtn from "./components/Signatures/AssignBtn.vue";
import CreateOrEdit from "./components/Signatures/CreateOrEdit.vue";
import SignaturesList from "./components/Signatures/List.vue";
import SignatureView from "./components/Signatures/View.vue";
import router from "./router";

const app = createApp({
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
    bugpublicationform: BugPublicationForm,
    commentpublicationform: CommentPublicationForm,
    crasheslist: CrashesList,
    crashstats: CrashStats,
    crashstatsgraph: CrashStatsGraph,
    createoredit: CreateOrEdit,
    inbox: Inbox,
    poolslist: PoolsList,
    poolview: PoolView,
    ppcselect: FullPPCSelect,
    providerkey: ProviderKey,
    signatureslist: SignaturesList,
    signatureview: SignatureView,
  },
});

app.use(router);
app.use(FloatingVue);
app.use(LoadingPlugin);

document.addEventListener("DOMContentLoaded", () => {
  app.mount("#app");
});
