import { createRouter, createWebHistory } from "vue-router";
import CovManagerBrowse from "./components/Covmanager/Browse.vue";
import CollectionsList from "./components/Covmanager/Collections.vue";
import CollectionsPatch from "./components/Covmanager/Patch.vue";
import ReportConfiguration from "./components/Covmanager/ReportConfiguration.vue";
import CovManagerReports from "./components/Covmanager/Reports.vue";
import CovManagerSummary from "./components/Covmanager/Summary.vue";
import CrashesList from "./components/Crashes/List.vue";
import PoolView from "./components/Pools/View.vue";
import SignaturesList from "./components/Signatures/List.vue";

const routes = [
  {
    // Be careful to keep this route up-to-date with the one in server/crashmanager/urls.py
    path: "/crashmanager/crashes/",
    name: "crashes-list",
    component: CrashesList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/crashmanager/urls.py
    path: "/crashmanager/crashes/watch/:sigid/",
    name: "crashes-watch",
    component: CrashesList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/crashmanager/urls.py
    path: "/crashmanager/signatures/",
    name: "signatures-list",
    component: SignaturesList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/crashmanager/urls.py
    path: "/taskmanager/pools/",
    name: "taskmanager-pools",
    component: PoolView,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/collections/",
    name: "covmanager-list",
    component: CollectionsList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/reports/",
    name: "covmanager-reports",
    component: CovManagerReports,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/collections/:id/browse/",
    name: "covmanager-browse",
    component: CovManagerBrowse,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/collections/diff/",
    name: "covmanager-browse-diffs",
    component: CovManagerBrowse,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/reportconfigurations/",
    name: "covmanager-reportconfigurations",
    component: ReportConfiguration,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/collections/patch/",
    name: "covmanager-patch",
    component: CollectionsPatch,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/covmanager/urls.py
    path: "/covmanager/collections/:id/summary/",
    name: "covmanager-summary",
    component: CovManagerSummary,
  },
];

// Create router instance
const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
