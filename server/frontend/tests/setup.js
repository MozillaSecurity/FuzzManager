import { config } from "@vue/test-utils";

// Setup global mocks
config.global.mocks = {
  $route: {
    hash: "",
    query: {},
    params: {},
    path: "/",
    name: null,
  },
};
