import { nextTick } from "vue";
import { createLocalVue, createWrapper } from "@vue/test-utils";
import VueRouter from "vue-router";
import { render } from "@testing-library/vue";
import Stats from "../src/components/CrashStats.vue";
import { crashStats, listBuckets } from "../src/api.js";
import { emptyCrashStats, crashStatsData, buckets } from "./fixtures.js";
import "lodash/throttle";

// This line will mock all calls to functions in ../src/api.js
jest.mock("../src/api.js");
// Mocking calls to lodash._throttle during tests
jest.mock("lodash/throttle", () => jest.fn((fn) => fn));

afterEach(jest.resetAllMocks);

test("empty stats doesn't break", async () => {
  const localVue = createLocalVue();
  localVue.use(VueRouter);
  const router = new VueRouter();

  crashStats.mockResolvedValue(emptyCrashStats);
  await render(Stats, {
    localVue,
    router,
    props: {
      restricted: false,
      providers: [],
      activityRange: 14,
    },
  });
  await nextTick();

  expect(crashStats).toHaveBeenCalledTimes(1);
  expect(crashStats).toHaveBeenCalledWith({
    ignore_toolfilter: "0",
  });
  expect(listBuckets).toHaveBeenCalledTimes(0);

  await nextTick();
  // Assert no signature is displayed in the table
  expect(document.querySelector("tbody tr")).toBeNull();
});

test("stats are shown", async () => {
  const localVue = createLocalVue();
  localVue.use(VueRouter);
  const router = new VueRouter();

  crashStats.mockResolvedValue(crashStatsData);
  listBuckets.mockResolvedValue(buckets);
  const { getByText } = await render(Stats, {
    localVue,
    router,
    props: {
      restricted: false,
      providers: [],
      activityRange: 14,
    },
  });
  await nextTick();

  expect(crashStats).toHaveBeenCalledTimes(1);
  expect(crashStats).toHaveBeenCalledWith({
    ignore_toolfilter: "0",
  });
  expect(listBuckets).toHaveBeenCalledTimes(1);
  await nextTick();
  await nextTick();
  await nextTick();

  // Assert two signatures are displayed in the table
  expect(document.querySelectorAll("tbody tr").length).toBe(2);
  getByText("A short description for bucket 1");
  const buttonLink = getByText("1630739");
  expect(buttonLink).toHaveProperty("href", buckets[0].bug_urltemplate);
  expect(buttonLink).toHaveProperty("target", "_blank");
  getByText("A short description for bucket 2");
  getByText("Assign an existing bug");
});

test("stats use hash params", async () => {
  crashStats.mockResolvedValue(crashStatsData);
  listBuckets.mockResolvedValue(buckets);
  const localVue = createLocalVue();
  const $route = { path: "/stats", hash: "#sort=id&alltools=1" };
  await render(Stats, {
    localVue,
    mocks: {
      $route,
    },
    props: {
      restricted: false,
      providers: [],
      activityRange: 14,
    },
  });
  await nextTick();

  expect(crashStats).toHaveBeenCalledTimes(1);
  expect(crashStats).toHaveBeenCalledWith({
    ignore_toolfilter: "1",
  });
  expect(listBuckets).toHaveBeenCalledTimes(1);
  await nextTick();
  await nextTick();
  await nextTick();

  expect(document.querySelectorAll("tbody tr").length).toBe(2);
});

test("stats are sortable", async () => {
  crashStats.mockResolvedValue(crashStatsData);
  listBuckets.mockResolvedValue(buckets);
  const localVue = createLocalVue();
  localVue.use(VueRouter);
  const router = new VueRouter();
  await render(Stats, {
    localVue,
    router,
    props: {
      restricted: false,
      providers: [],
      activityRange: 14,
    },
  });
  await nextTick();

  expect(crashStats).toHaveBeenCalledTimes(1);
  expect(listBuckets).toHaveBeenCalledTimes(1);
  await nextTick();
  await nextTick();
  await nextTick();

  let rows = document.querySelectorAll("tbody tr");
  expect(rows.length).toBe(2);
  // sorted by daily count by default
  expect(rows[0].querySelector("td").textContent).toBe("2");
  expect(rows[1].querySelector("td").textContent).toBe("1");
  expect(router.currentRoute.hash).toBe("");

  await createWrapper(document.querySelector("thead th")).trigger("click");
  await nextTick();

  rows = document.querySelectorAll("tbody tr");
  expect(rows.length).toBe(2);
  // sorted by id now
  expect(rows[0].querySelector("td").textContent).toBe("1");
  expect(rows[1].querySelector("td").textContent).toBe("2");
  expect(router.currentRoute.hash).toBe("#sort=id");

  await createWrapper(document.querySelector("thead th")).trigger("click");
  await nextTick();

  rows = document.querySelectorAll("tbody tr");
  expect(rows.length).toBe(2);
  // sorted by -id now
  expect(rows[0].querySelector("td").textContent).toBe("2");
  expect(rows[1].querySelector("td").textContent).toBe("1");
  expect(router.currentRoute.hash).toBe("#sort=-id");

  await createWrapper(document.querySelector("thead th + th")).trigger(
    "click",
    { ctrlKey: true }
  );
  await nextTick();

  expect(router.currentRoute.hash).toBe("#sort=shortDescription,-id");
});
