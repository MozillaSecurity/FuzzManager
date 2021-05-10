import VueRouter from "vue-router";

import List from "./components/Crashes/List.vue";

const routes = [
  {
    path: "/crashmanager/crashes2",
    name: "crashes-list",
    component: List,
  },
];

const router = new VueRouter({
  mode: "history",
  routes,
});

export default router;
