<template>
  <!-- Legend component for toggling dataset visibility -->
  <LineChartLegend :datasets="dataSets" :on-toggle="handleToggleDataset" />
  <!-- SVG element for rendering the line chart -->
  <svg :id="chartId" style="height: 50vh"></svg>
</template>

<script>
import { defineComponent, onMounted, onUnmounted, ref } from "vue";
import * as d3 from "d3";
import LineChartLegend from "./LineChartLegend.vue";

export default defineComponent({
  name: "LineChart",
  components: { LineChartLegend },
  props: {
    chartId: {
      type: String,
      default: "line-chart",
    },
    chartdata: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    // Reactive state for chart data
    const dataSets = ref(props.chartdata.datasets || []);
    const labels = ref(props.chartdata.labels || []);

    let svgContainer;

    /**
     * Handles toggling the visibility of datasets
     * @param {String} datasetId - The ID of the dataset to toggle
     */
    const handleToggleDataset = (datasetId) => {
      const newDataSets = dataSets?.value.map((data) =>
        data.id === datasetId
          ? {
              ...data,
              hidden: !data?.hidden,
            }
          : data,
      );
      dataSets.value = newDataSets;
      renderChart();
    };

    /**
     * Creates and renders the line chart using D3.js
     */
    const renderChart = () => {
      // Select the SVG container by ID
      svgContainer = d3.select(`#${props.chartId}`);

      // Clear previous chart elements
      svgContainer.selectAll("*").remove();

      if (!svgContainer) return;

      // Chart dimensions and margins
      const margins = { top: 20, right: 60, bottom: 40, left: 160 };
      const chartWidth = 1880;
      const chartHeight = 600;

      // Set up the SVG container dimensions and viewBox
      svgContainer
        .attr("width", "100%")
        .attr("height", chartHeight)
        .attr("viewBox", [0, 0, chartWidth, chartHeight])
        .attr("style", "max-width: 100%; height: auto; height: intrinsic;");

      // Define the X-axis scale based on labels
      const xScale = d3
        .scalePoint()
        .domain(labels?.value)
        .range([margins.left, chartWidth - margins.right]);

      // Append X-axis to the chart
      svgContainer
        .append("g")
        .attr("transform", `translate(0,${chartHeight - margins.bottom})`)
        .call(d3.axisBottom(xScale))
        .selectAll("text")
        .style("font-size", "16px");

      const yAxis0Datasets = [];
      const yAxis1Datasets = [];

      dataSets?.value.forEach((dataset) => {
        if (dataset.hidden) return;

        // Group by yAxisID
        if (dataset.yAxisID === "y-axis-0") {
          yAxis0Datasets.push(dataset);
        } else if (dataset.yAxisID === "y-axis-1") {
          yAxis1Datasets.push(dataset);
        }
      });

      const yAxis0DataValues = yAxis0Datasets.flatMap((d) => d.data);
      const yScale0 = d3
        .scaleLinear()
        .domain([Math.floor(d3.min(yAxis0DataValues) || 1), 100])
        .range([chartHeight - margins.bottom, margins.top]);

      // Append the first Y-axis to the chart
      svgContainer
        .append("g")
        .attr("transform", `translate(${margins.left - 50}, 0)`)
        .attr("opacity", yAxis0Datasets.length ? 1 : 0.3)
        .call(d3.axisLeft(yScale0))
        .selectAll("text")
        .style("font-size", "16px");
      svgContainer
        .append("g")
        .attr("transform", `translate(${margins.left}, 0)`)
        .call(d3.axisLeft(yScale0))
        .call((g) =>
          g
            .selectAll(".tick line")
            .clone()
            .attr("x2", chartWidth - margins.left - margins.right)
            .attr("stroke-opacity", 0.3),
        )
        .call((g) => g.selectAll(".tick text").remove());

      const yAxis1DataValues = yAxis1Datasets.flatMap((d) => d.data);
      const yScale1 = d3
        .scaleLinear()
        .domain(
          yAxis1Datasets.length
            ? [
                Math.floor(d3.min(yAxis1DataValues)),
                Math.round(d3.max(yAxis1DataValues)),
              ]
            : [0, 1],
        )
        .range([chartHeight - margins.bottom, margins.top]);

      // Append the second Y-axis to the chart
      svgContainer
        .append("g")
        .attr("transform", `translate(${margins.left - 100}, 0)`)
        .attr("opacity", yAxis1Datasets.length ? 1 : 0.3)
        .call(d3.axisLeft(yScale1))
        .selectAll("text")
        .style("font-size", "16px");

      // Additional setup for the third Y-axis (if needed)
      const yScale3 = d3
        .scaleLinear()
        .range([chartHeight - margins.bottom, margins.top]);

      svgContainer
        .append("g")
        .attr("transform", `translate(${margins.left}, 0)`)
        .attr("opacity", 0.5)
        .call(d3.axisLeft(yScale3))
        .selectAll("text")
        .style("font-size", "16px");

      svgContainer
        .append("g")
        .attr("transform", `translate(${chartWidth - margins.right}, 0)`)
        .attr("opacity", 0.5)
        .call(d3.axisLeft(yScale3))
        .call((g) => g.selectAll(".tick text").remove());

      svgContainer
        .append("g")
        .attr("transform", `translate(${margins.left}, 0)`)
        .attr("opacity", 0.5)
        .call(d3.axisLeft(yScale3))
        .call((g) =>
          g
            .selectAll(".tick line")
            .clone()
            .attr("x2", chartWidth - margins.left - margins.right)
            .attr("stroke-opacity", 0.5),
        )
        .call((g) => g.selectAll(".tick text").remove());

      // Define tooltip container
      const tooltip = d3
        .select("body")
        .append("div")
        .attr("class", "chart-tooltip")
        .style("position", "absolute")
        .style("background", "#000000")
        .style("border", "1px solid #ccc")
        .style("border-radius", "4px")
        .style("padding", "8px")
        .style("pointer-events", "none")
        .style("font-size", "12px")
        .style("color", "#fff")
        .style("opacity", 0);

      // Render lines for visible datasets
      dataSets?.value.forEach((dataset, index) => {
        if (dataset.hidden) return;
        const yScale = dataset.yAxisID === "y-axis-0" ? yScale0 : yScale1;

        // Define line generator function
        const lineGenerator = d3
          .line()
          .x((_, i) => xScale(labels?.value[i]))
          .y((d) => yScale(d));

        // Add markers for each data point and tooltip
        dataset.data.forEach((point, i) => {
          svgContainer
            .append("circle")
            .attr("cx", xScale(labels.value[i]))
            .attr("cy", yScale(point))
            .attr("r", 5)
            .attr("fill", dataset.pointBackgroundColor || "black")
            .attr("opacity", 0.8)
            .attr("cursor", "pointer")
            .attr("stroke", dataset.borderColor || "none")
            .attr("stroke-width", 1)
            .on("mouseover", (event) => {
              tooltip
                .style("opacity", 0.8)
                .html(
                  `<strong>Label:</strong> ${
                    labels.value[i]
                  }<br><strong>Value:</strong> ${point}`,
                )
                .style("left", event.pageX + 10 + "px")
                .style("top", event.pageY - 28 + "px");
            })
            .on("mousemove", (event) => {
              tooltip
                .style("left", event.pageX + 10 + "px")
                .style("top", event.pageY - 28 + "px");
            })
            .on("mouseout", () => {
              tooltip.style("opacity", 0);
            });
        });

        // Append the line to the chart
        svgContainer
          .append("path")
          .datum(dataset.data)
          .attr("fill", "none")
          .attr("stroke", dataset.borderColor || d3.schemeCategory10[index])
          .attr("stroke-width", 4)
          .attr("d", lineGenerator)
          .attr("opacity", 0)
          .transition()
          .duration(1000)
          .attr("opacity", 1);
      });
    };

    onMounted(() => {
      renderChart();
    });

    onUnmounted(() => {
      d3.select(`#${props.chartId}`).select("svg").remove();
    });

    return {
      dataSets,
      handleToggleDataset,
      renderChart,
    };
  },
});
</script>
