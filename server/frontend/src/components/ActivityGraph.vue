<template><span></span></template>

<script>
import * as d3 from "d3";

const hour_ms = 60 * 60 * 1000;
const day_ms = 24 * hour_ms;

function crash_history_to_range(fm_data, start, step, stop, clip) {
  /*
   * FuzzManager returns an array of `{ begin: "isodate", count: n }`
   * objects, where begin is the start of a one hour monitoring
   * period. Periods where no count was recorded will not be included.
   *
   * This function generates a continuous series where gaps are filled
   * with 0 counts, and values are clipped to a maximum.
   *
   * fm_data: Array[ Object { begin: String (ISO date), count: Number } ]
   * start: Number (timestamp in ms)
   * step: Number (ms)
   * end: Number (timestamp in ms)
   * clip: Number
   *
   * returns: Array[ Object { begin: Number (timestamp in ms), count: Number } ]
   */
  const result = [];
  let cp = start,
    ncp = cp + step;
  const next_fm_date = (idx) => {
    if (idx < fm_data.length) return new Date(fm_data[idx].begin).valueOf();
    else return null;
  };
  let idx_date = next_fm_date(0);

  for (let idx = 0; cp < stop; cp += step, ncp += step) {
    const next = { date: cp, count: 0 };

    while (idx_date !== null && cp <= idx_date && idx_date < ncp) {
      next.count += fm_data[idx].count;
      idx++;
      idx_date = next_fm_date(idx);
    }
    if (next.count > clip) next.count = clip;

    result.push(next);
  }
  return result;
}

export default {
  props: {
    range: {
      // time-span to graph, in days
      type: Number,
      required: true,
    },
    data: {
      type: Array,
      required: true,
    },
  },
  mounted() {
    // set the dimensions and margins of the graph
    const margin = { top: 5, right: 5, bottom: 0, left: 5 };
    const width = 150 - margin.left - margin.right;
    const height = 40 - margin.top - margin.bottom;

    /*
     * format data for d3
     * start is current time (rounded up to next hour) - CLEANUP_DAYS ..
     */
    const next_hour_ms = (() => {
      const now = new Date().valueOf();
      return now + hour_ms - (now % hour_ms);
    })();
    const clip = 10;
    const data = crash_history_to_range(
      this.data,
      next_hour_ms - this.range * day_ms,
      hour_ms,
      next_hour_ms,
      clip
    );

    // append the svg object to the body of the page
    const svg = d3
      .select(this.$el)
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Add X axis
    const x = d3
      .scaleTime()
      .domain(d3.extent(data, (d) => d.date))
      .range([0, width]);

    // Add Y axis
    const y = d3.scaleLinear().domain([0, 10]).range([height, 0]);

    // Add the area
    svg
      .append("path")
      .datum(data, (d) => d.count)
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 1.5)
      .attr(
        "d",
        d3
          .line()
          .x((d) => x(d.date))
          .y((d) => y(d.count))
      );
  },
};
</script>
