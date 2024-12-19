<template><span></span></template>

<script>
import * as d3 from "d3";
import { defineComponent, getCurrentInstance, watch } from "vue";

export default defineComponent({
  props: {
    data: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const instance = getCurrentInstance();

    // Watch for data changes
    watch(
      () => props.data,
      () => {
        /*
         * Based on https://observablehq.com/@mbostock/revenue-by-music-format-1973-2018
         */

        // set the dimensions and margins of the graph
        const margin = { top: 3, right: 3, bottom: 10, left: 20 };
        const width = 800;
        const height = 150;

        d3.select("svg").remove();
        const svg = d3
          .select(instance.vnode.el)
          .append("svg")
          .attr("viewBox", [0, 0, width, height]);

        const colors = new Map([
          ["Out of Tool Filter", "#F1CF63"],
          ["In Tool Filter", "#7AAAD0"],
        ]);

        const inFilterDataByDay = [];
        const outFilterDataByDay = [];
        const days = Math.floor(props.data.outFilter.length / 24);

        for (let i = 0; i < props.data.outFilter.length; ++i) {
          const day = Math.floor(i / 24);
          if (day >= inFilterDataByDay.length) {
            inFilterDataByDay.push(0);
            outFilterDataByDay.push(0);
          }
          inFilterDataByDay[day] += props.data.inFilter[i];
          outFilterDataByDay[day] += props.data.outFilter[i];
        }

        const data = [];
        for (let i = 0; i < outFilterDataByDay.length; ++i) {
          const p = i - outFilterDataByDay.length + 1;
          data.push({
            name: "Out of Tool Filter",
            time: p - 0.5,
            value: outFilterDataByDay[i],
          });
          data.push({
            name: "In Tool Filter",
            time: p - 0.5,
            value: inFilterDataByDay[i],
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
                (d) => d.name,
              )
              .values(),
          )
          .map((s) => (s.forEach((d) => (d.data = d.data.get(s.key))), s));

        const color = d3
          .scaleOrdinal()
          .domain(colors.keys())
          .range(colors.values());

        // Add X axis
        const xData = d3
          .scaleBand()
          .domain(data.map((d) => d.time))
          .range([margin.left, width - margin.right]);
        const xAxisData = d3
          .scaleLinear()
          .domain([0, days])
          .range([margin.left, width - margin.right]);
        const xAxis = (g) =>
          g
            .attr("transform", `translate(0,${height - margin.bottom})`)
            .call(
              d3
                .axisBottom(xAxisData)
                .ticks(days + 1)
                .tickFormat((x) => `${x - days}d`)
                .tickSize(2),
            )
            .call((g) => {
              g.select(".domain").attr("stroke-width", 0.5);
              g.select(".tick:first-of-type text").remove();
              g.select(".tick:last-of-type text").remove();
              g.selectAll(".tick text").attr("y", 4);
              g.selectAll(".tick line").attr("stroke-width", 0.5);
            })
            .attr("font-size", 6);

        // Add Y axis
        const y = d3
          .scaleLinear()
          .domain(d3.extent(series.flat(2)))
          .range([height - margin.bottom, margin.top]);
        const yAxis = (g) =>
          g
            .attr("transform", `translate(${margin.left},0)`)
            .call(d3.axisLeft(y).tickSize(2))
            .call((g) => {
              g.select(".domain").remove();
              g.selectAll(".tick text").attr("x", -3);
              g.selectAll(".tick line").attr("stroke-width", 0.5);
            })
            .attr("font-size", 6);

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
              .attr("x", (d) => xData(d.data.time))
              .attr("y", (d) => y(d[1]))
              .attr("width", xData.bandwidth())
              .attr("height", (d) => y(d[0]) - y(d[1]))
              .append("title")
              .text((d) => `${d.data.name}: ${d.data.value}`),
          );
        svg.append("g").call(yAxis);
        svg.append("g").call(xAxis);
      },
    );
  },
});
</script>
