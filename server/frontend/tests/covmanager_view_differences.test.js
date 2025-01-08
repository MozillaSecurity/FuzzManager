import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { covManagerDiffStats, reportMetadata, rvLists } from "../src/api";
import Browse from "../src/components/Covmanager/Browse.vue";
import LineChart from "../src/components/Covmanager/LineChart.vue";

import { covManagerData, mockChartData, rvListData } from "./fixtures";

// This line will mock all calls to functions in ../src/api.js
jest.mock("../src/api.js");

afterEach(() => {
  document.body.innerHTML = "";
  jest.clearAllMocks();
});

test("renders a line chart with the given data", async () => {
  const wrapper = mount(LineChart, {
    props: {
      chartId: "custom-line-chart",
      chartdata: mockChartData,
    },
  });

  // Wait for D3 to update the chart
  await wrapper.vm.$nextTick();
  const svg = wrapper.find("svg#custom-line-chart");
  expect(svg.exists()).toBe(true);
});

test("renders diff graph successfully", async () => {
  covManagerDiffStats.mockResolvedValue(covManagerData);
  rvLists.mockResolvedValue(rvListData);
  rvLists.mockResolvedValue(rvListData);

  window.scroll = jest.fn();

  const propsData = {
    urls: {
      rc: "/covmanager/reportconfigurations/api/",
      reports_api: "/covmanager/reports/api/",
    },
    diffApi: true,
    ids: [],
  };

  const wrapper = mount(Browse, {
    props: propsData,
  });

  await nextTick();

  expect(covManagerDiffStats).toHaveBeenCalledTimes(1);
  expect(covManagerDiffStats).toHaveBeenCalledWith({
    path: "",
    cb: expect.any(Function),
    params: {},
  });

  expect(rvLists).toHaveBeenCalledTimes(1);
  expect(rvLists).toHaveBeenCalledWith({ __exclude: "directives" });

  expect(reportMetadata).not.toHaveBeenCalled();

  await nextTick();
  await nextTick();

  expect(wrapper.exists()).toBe(true);
  expect(wrapper.vm).toBeTruthy();

  expect(wrapper.vm.loading).toBe(false);
  expect(Array.isArray(wrapper.vm.chartdata.datasets)).toBe(true);
  expect(wrapper.vm.collectionId).toBe(undefined);

  const tables = wrapper.findAll("table");

  expect(tables.length).toBe(1);

  const diffTable = tables[0];
  let rows = diffTable.findAll("tbody tr");
  expect(rows.length).toBe(3);

  expect(rows[0].find("td").text()).toBe("a");
  expect(rows[1].find("td").text()).toBe("b");
  expect(rows[2].find("td").text()).toBe("main.c");
  expect(window.location.hash.includes("p=a")).toBe(false);

  // click first row
  await rows[0].trigger("click");
  await nextTick();
  await nextTick();

  expect(window.location.hash.includes("p=a")).toBe(true);

  // go back to previous page
  // const canvas = wrapper.find("canvas");

  // expect(canvas.exists()).toBe(true);
  // expect(canvas.exists()).toBe(true);
  // expect(canvas.attributes("id")).toBe("line-chart");
});
