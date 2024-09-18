import VueRouter from "vue-router";

import ReportsList from "./components/Reports/List.vue";
import BucketsList from "./components/Buckets/List.vue";

const routes = [
  {
    // Be careful to keep this route up-to-date with the one in server/reportmanager/urls.py
    path: "/reportmanager/reports/",
    name: "reports-list",
    component: ReportsList,
  },
  {
    // Be careful to keep this route up-to-date with the one in server/reportmanager/urls.py
    path: "/reportmanager/buckets/",
    name: "buckets-list",
    component: BucketsList,
  },
];

const router = new VueRouter({
  mode: "history",
  routes,
});

export default router;
