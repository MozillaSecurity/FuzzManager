<template><span></span></template>

<script>
import * as d3 from "d3";

export default {
  props: {
    data: {
      type: Object,
      required: true,
    },
  },
  watch: {
    data: function () {
      /*
       *Based on https://observablehq.com/@mbostock/revenue-by-music-format-1973-2018
       */

      // set the dimensions and margins of the graph
      const margin = { top: 5, right: 5, bottom: 20, left: 40 };
      const width = 2500;
      const height = 300;

      d3.select("svg").remove();
      const svg = d3
        .select(this.$el)
        .append("svg")
        .attr("viewBox", [0, 0, width, height]);

      const colors = new Map([
        ["Out of Tool Filter", "#F1CF63"],
        ["In Tool Filter", "#7AAAD0"],
      ]);

      const data = [];
      for (let i = 0; i < this.data.outFilter.length; ++i) {
        const p = i - this.data.outFilter.length + 1;
        data.push({
          name: "Out of Tool Filter",
          time: p,
          value: this.data.outFilter[i],
        });
        data.push({
          name: "In Tool Filter",
          time: p,
          value: this.data.inFilter[i],
        });
      }

      // format data
      const series = d3
        .stack()
        .keys(colors.keys())
        .value((group, key) => group.get(key).value)
        .order(d3.stackOrderReverse)(
          d3
            .rollup(
              data,
              ([d]) => d,
              (d) => d.time,
              (d) => d.name
            )
            .values()
        )
        .map((s) => (s.forEach((d) => (d.data = d.data.get(s.key))), s));

      const color = d3
        .scaleOrdinal()
        .domain(colors.keys())
        .range(colors.values());

      // Add X axis
      const x = d3
        .scaleBand()
        .domain(data.map((d) => d.time))
        .rangeRound([margin.left, width - margin.right]);
      const xAxis = (g) =>
        g.attr("transform", `translate(0,${height - margin.bottom})`).call(
          d3
            .axisBottom(x)
            .tickFormat((x) => (x ? `${x / -24}d` : "now"))
            .tickValues(x.domain().filter((d, i) => !((i + 1) % 24)))
            .tickSizeOuter(0)
        );

      // Add Y axis
      const y = d3
        .scaleLinear()
        .domain(d3.extent(series.flat(2)))
        .range([height - margin.bottom, margin.top]);
      const yAxis = (g) =>
        g
          .attr("transform", `translate(${margin.left},0)`)
          .call(d3.axisLeft(y).tickSizeOuter(0))
          .call((g) => g.select(".domain").remove());

      // create the chart
      svg
        .append("g")
        .selectAll("g")
        .data(series)
        .join("g")
        .attr("fill", ({ key }) => color(key))
        .call((g) =>
          g
            .selectAll("rect")
            .data((d) => d)
            .join("rect")
            .attr("x", (d) => x(d.data.time))
            .attr("y", (d) => y(d[1]))
            .attr("width", x.bandwidth())
            .attr("height", (d) => y(d[0]) - y(d[1]))
            .append("title")
            .text((d) => `${d.data.name}: ${d.data.value}`)
        );
      svg.append("g").call(yAxis);
      svg.append("g").call(xAxis);
    },
  },
};
</script>
