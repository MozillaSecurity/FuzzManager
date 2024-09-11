import VueRouter from "vue-router";

import ReportsList from "./components/Reports/List.vue";
import SignaturesList from "./components/Signatures/List.vue";

const routes = [
  {
    // Be careful to keep this route up-to-date with the one in server/reportmanager/urls.py
    path: "/reportmanager/reports/",
    name: "reports-list",
    component: ReportsList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/reportmanager/urls.py
    path: "/reportmanager/reports/watch/:sigid/",
    name: "reports-watch",
    component: ReportsList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/reportmanager/urls.py
    path: "/reportmanager/signatures/",
    name: "signatures-list",
    component: SignaturesList,
  },
];

const router = new VueRouter({
  mode: "history",
  routes,
});

export default router;
