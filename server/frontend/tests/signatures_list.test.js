import { render } from "@testing-library/vue";
import "lodash/throttle";
import { nextTick } from "vue";
import { listBuckets } from "../src/api.js";
import List from "../src/components/Signatures/List.vue";
import { buckets, emptyBuckets } from "./fixtures.js";

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

  const { container } = await render(List, {
    props: {
      watchUrl: "/crashmanager/signatures/watch/",
      providers: [],
      activityRange: 14,
    },
    global: {
      mocks: {
        $router: [],
      },
    },
  });

  await nextTick();

  expect(listBuckets).toHaveBeenCalledTimes(1);
  expect(listBuckets).toHaveBeenCalledWith({
    vue: "1",
    ignore_toolfilter: "0",
    query: defaultQueryStr,
  });

  await nextTick();

  // Assert no signature is displayed in the table
  expect(container.querySelector("tbody tr")).toBeNull();
});

test("signature list has two buckets", async () => {
  listBuckets.mockResolvedValue(buckets);

  const { getByText, container } = await render(List, {
    props: {
      watchUrl: "/crashmanager/signatures/watch/",
      providers: [],
      activityRange: 14,
    },
    global: {
      mocks: {
        $router: [],
      },
    },
  });

  await nextTick();

  expect(listBuckets).toHaveBeenCalledTimes(1);
  expect(listBuckets).toHaveBeenCalledWith({
    vue: "1",
    ignore_toolfilter: "0",
    query: defaultQueryStr,
  });

  await nextTick();

  // Assert two signatures (one assigned to a bug, the other not) are displayed in the table
  expect(container.querySelectorAll("tbody tr")).toHaveLength(2);
  getByText("A short description for bucket 1");
  const buttonLink = getByText("1630739");
  expect(buttonLink.getAttribute("href")).toBe(buckets[0].bug_urltemplate);
  expect(buttonLink.getAttribute("target")).toBe("_blank");
  getByText("A short description for bucket 2");
  getByText("Assign an existing bug");
});
