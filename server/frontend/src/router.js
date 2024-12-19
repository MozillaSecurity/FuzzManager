import { createRouter, createWebHistory } from "vue-router";
import CrashesList from "./components/Crashes/List.vue";
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
];

// Create router instance
const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
