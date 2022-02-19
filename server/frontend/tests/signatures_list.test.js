import Vue from "vue";
import { createLocalVue } from "@vue/test-utils";
import VueRouter from "vue-router";
import { render } from "@testing-library/vue";
import List from "../src/components/Signatures/List.vue";
import { listBuckets } from "../src/api.js";
import { emptyBuckets, buckets } from "./fixtures.js";
import "lodash/throttle";

const localVue = createLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

// This line will mock all calls to functions in ../src/api.js
jest.mock("../src/api.js");
// Mocking calls to lodash._throttle during tests
jest.mock("lodash/throttle", () => jest.fn((fn) => fn));

afterEach(jest.resetAllMocks);

const defaultQueryStr = `{
  "op": "AND",
  "bug__isnull": true
}`;

test("signature list has no buckets", async () => {
  listBuckets.mockResolvedValue(emptyBuckets);
  await render(List, {
    localVue,
    router,
    props: {
      watchUrl: "/crashmanager/signatures/watch/",
      providers: [],
      activityRange: 14,
    },
  });
  await Vue.nextTick();

  expect(listBuckets).toHaveBeenCalledTimes(1);
  expect(listBuckets).toHaveBeenCalledWith({
    vue: "1",
    ignore_toolfilter: "0",
    query: defaultQueryStr,
  });

  await Vue.nextTick();
  // Assert no signature is displayed in the table
  expect(document.querySelector("tbody tr")).toBeNull();
});

test("signature list has two buckets", async () => {
  listBuckets.mockResolvedValue(buckets);
  const { getByText } = await render(List, {
    localVue,
    router,
    props: {
      watchUrl: "/crashmanager/signatures/watch/",
      providers: [],
      activityRange: 14,
    },
  });
  await Vue.nextTick();

  expect(listBuckets).toHaveBeenCalledTimes(1);
  expect(listBuckets).toHaveBeenCalledWith({
    vue: "1",
    ignore_toolfilter: "0",
    query: defaultQueryStr,
  });

  await Vue.nextTick();
  // Assert two signatures (one assigned to a bug, the other not) are displayed in the table
  expect(document.querySelectorAll("tbody tr").length).toBe(2);
  getByText("A short description for bucket 1");
  const buttonLink = getByText("1630739");
  expect(buttonLink).toHaveProperty("href", buckets[0].bug_urltemplate);
  expect(buttonLink).toHaveProperty("target", "_blank");
  getByText("A short description for bucket 2");
  getByText("Assign an existing bug");
});
