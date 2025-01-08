import { mount } from "@vue/test-utils";
import Chart from "chart.js/auto";
import { nextTick } from "vue";
import { covManagerDiffStats, reportMetadata, rvLists } from "../src/api";
import Browse from "../src/components/Covmanager/Browse.vue";
import LineChart from "../src/components/Covmanager/LineChart.vue";

import { covManagerData, mockChartData, rvListData } from "./fixtures";

// This line will mock all calls to functions in ../src/api.js
jest.mock("../src/api.js");

// Mock Chart.js
jest.mock("chart.js/auto", () => {
  return jest.fn().mockImplementation(() => ({
    destroy: jest.fn(),
    update: jest.fn(),
  }));
});

const setupChartDom = () => {
  // Create canvas element that Chart.js needs
  const canvas = document.createElement("canvas");
  canvas.id = "test-chart";
  document.body.appendChild(canvas);
};

afterEach(() => {
  document.body.innerHTML = "";
  jest.clearAllMocks();
});

test("renders chart with provided data", async () => {
  setupChartDom();
  const wrapper = mount(LineChart, {
    props: {
      chartId: "test-chart",
      chartdata: mockChartData,
    },
  });

  await nextTick();

  // Check if canvas exists
  const canvas = wrapper.find("canvas");
  expect(canvas.exists()).toBe(true);
  expect(canvas.attributes("id")).toBe("test-chart");

  // Verify Chart.js was initialized
  expect(Chart).toHaveBeenCalledTimes(1);

  // Check if chart options were passed correctly
  const chartCall = Chart.mock.calls[0];
  expect(chartCall[1].data.labels).toEqual(mockChartData.labels);
  expect(chartCall[1].data.datasets).toEqual(mockChartData.datasets);
});

test("destroys chart instance on unmount", async () => {
  setupChartDom();
  const wrapper = mount(LineChart, {
    props: {
      chartId: "test-chart",
      chartdata: mockChartData,
    },
  });

  await nextTick();

  const chartInstance = Chart.mock.results[0].value;
  wrapper.unmount();

  expect(chartInstance.destroy).toHaveBeenCalledTimes(1);
});

test("chart has correct dimensions", () => {
  setupChartDom();
  const wrapper = mount(LineChart, {
    props: {
      chartId: "test-chart",
      chartdata: mockChartData,
    },
  });

  const container = wrapper.find("div");
  expect(container.attributes("style")).toContain("width: 100%");
  expect(container.attributes("style")).toContain("height: 50vh");
});

test("updates chart when data changes", async () => {
  setupChartDom();
  const wrapper = mount(LineChart, {
    props: {
      chartId: "test-chart",
      chartdata: mockChartData,
    },
  });

  await nextTick();

  const newChartData = {
    labels: ["Day 1", "Day 2", "Day 3", "Day 4"],
    datasets: [
      {
        label: "Coverage",
        data: [75, 80, 85, 90],
        borderColor: "rgb(75, 192, 192)",
        tension: 0.1,
        created: ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
        deltas: ["+5", "+5", "+5"],
        unit: "%",
      },
    ],
  };

  await wrapper.setProps({ chartdata: newChartData });
  await nextTick();

  // Verify the internal chartData ref was updated
  expect(wrapper.vm.chartdata.labels).toEqual(newChartData.labels);
  expect(wrapper.vm.chartdata.datasets).toEqual(newChartData.datasets);
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
  const canvas = wrapper.find("canvas");

  expect(canvas.exists()).toBe(true);
  expect(canvas.exists()).toBe(true);
  expect(canvas.attributes("id")).toBe("line-chart");
});
