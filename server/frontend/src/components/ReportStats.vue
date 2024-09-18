<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-bar-chart-fill"></i> Statistics
    </div>
    <div class="panel-body">
      <div>
        Total reports in:<br />
        ... last hour: {{ totals[0] }}<br />
        ... last day: {{ totals[1] }}<br />
        ... last week: {{ totals[2] }}
      </div>
    </div>
    <div class="panel-body">
      <reportstatsgraph :data="graphData" />
    </div>
    <div class="table-responsive">
      <table class="table table-condensed table-hover table-bordered table-db">
        <thead>
          <tr>
            <th
              v-on:click.exact="sortBy('id')"
              v-on:click.ctrl.exact="addSort('id')"
              :class="{
                active: sortKeys.includes('id') || sortKeys.includes('-id'),
              }"
            >
              Bucket
            </th>
            <th
              v-on:click.exact="sortBy('short_description')"
              v-on:click.ctrl.exact="addSort('short_description')"
              :class="{
                active:
                  sortKeys.includes('short_description') ||
                  sortKeys.includes('short_description'),
              }"
            >
              Short Description
            </th>
            <th>Activity</th>
            <th
              v-on:click.exact="sortBy('counts[0]')"
              v-on:click.ctrl.exact="addSort('counts[0]')"
              :class="{
                active:
                  sortKeys.includes('counts[0]') ||
                  sortKeys.includes('-counts[0]'),
              }"
            >
              Reports (last hour)
            </th>
            <th
              v-on:click.exact="sortBy('counts[1]')"
              v-on:click.ctrl.exact="addSort('counts[1]')"
              :class="{
                active:
                  sortKeys.includes('counts[1]') ||
                  sortKeys.includes('-counts[1]'),
              }"
            >
              Reports (last day)
            </th>
            <th
              v-on:click.exact="sortBy('counts[2]')"
              v-on:click.ctrl.exact="addSort('counts[2]')"
              :class="{
                active:
                  sortKeys.includes('counts[2]') ||
                  sortKeys.includes('-counts[2]'),
              }"
            >
              Reports (last week)
            </th>
            <th
              v-on:click.exact="sortBy('bug__external_id')"
              v-on:click.ctrl.exact="addSort('bug__external_id')"
              :class="{
                active:
                  sortKeys.includes('bug__external_id') ||
                  sortKeys.includes('-bug__external_id'),
              }"
            >
              External Bug
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7">
              <ClipLoader class="m-strong" :color="'black'" :size="'50px'" />
            </td>
          </tr>
          <tr v-else v-for="bucket of sortedBucketData" :key="bucket.id">
            <td>
              <a title="View bucket" :href="bucket.view_url">{{ bucket.id }}</a>
            </td>
            <td class="wrap-anywhere">
              <span class="two-line-limit">{{ bucket.short_description }}</span>
            </td>
            <td>
              <activitygraph
                :data="bucket.report_history"
                :range="activityRange"
              />
            </td>
            <td>{{ bucket.counts[0] }}</td>
            <td>{{ bucket.counts[1] }}</td>
            <td>{{ bucket.counts[2] }}</td>
            <td>
              <a
                v-if="bucket.bug && bucket.bug_urltemplate"
                :class="{ fixedbug: bucket.bug_closed }"
                :href="bucket.bug_urltemplate"
                target="_blank"
              >
                {{ bucket.bug }}
              </a>
              <p v-else-if="bucket.bug">
                {{ bucket.bug }} on {{ bucket.bug_hostname }}
              </p>
              <assignbutton v-else :bucket="bucket.id" :providers="providers" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import _throttle from "lodash/throttle";
import swal from "sweetalert";
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
import { errorParser, E_SERVER_ERROR, multiSort } from "../helpers";
import * as api from "../api";
import AssignBtn from "./Buckets/AssignBtn.vue";
import ActivityGraph from "./ActivityGraph.vue";
import ReportStatsGraph from "./ReportStatsGraph.vue";

export default {
  mixins: [multiSort],
  components: {
    ClipLoader,
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
    reportstatsgraph: ReportStatsGraph,
  },
  data: function () {
    const defaultSortKeys = ["-counts[0]"];
    const validSortKeys = [
      "bug__external_id",
      "counts[0]",
      "counts[1]",
      "counts[2]",
      "id",
      "short_description",
    ];
    return {
      defaultSortKeys: defaultSortKeys,
      graphData: [],
      loading: false,
      // [Bucket()]
      bucketData: [],
      sortKeys: [...defaultSortKeys],
      // [hour, day, week]
      totals: [],
      validSortKeys: validSortKeys,
    };
  },
  created: function () {
    this.fetch();
  },
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    providers: {
      type: Array,
      required: true,
    },
  },
  computed: {
    sortedBucketData: function () {
      return this.sortData(this.bucketData);
    },
  },
  methods: {
    // get stats
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.updateHash();
        try {
          // fetch stats
          const stats = await api.reportStats();

          // process result
          this.totals = stats.totals;
          this.graphData = stats.graphData;

          // then get buckets for those stats
          if (Object.keys(stats.frequentBuckets).length) {
            const bucketData = await api.listBuckets({
              vue: "1",
              query: JSON.stringify({
                op: "AND",
                id__in: Object.keys(stats.frequentBuckets),
              }),
            });
            Object.keys(stats.frequentBuckets).forEach((x) =>
              bucketData.forEach((b) => {
                if (b.id == x) b.counts = stats.frequentBuckets[x];
              }),
            );
            this.bucketData = bucketData;
          } else {
            this.bucketData = [];
          }
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            swal("Oops", E_SERVER_ERROR, "error");
            this.loading = false;
          } else {
            // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
            // eslint-disable-next-line no-console
            console.debug(errorParser(err));
            this.$router.go(0);
            return;
          }
        }
        this.loading = false;
      },
      500,
      { trailing: true },
    ),
    updateHash: function () {
      const hash = {};

      this.updateHashSort(hash);
      if (Object.entries(hash).length) {
        const routeHash =
          "#" +
          Object.entries(hash)
            .map((kv) => kv.join("="))
            .join("&");
        if (this.$route.hash !== routeHash)
          this.$router.push({ path: this.$route.path, hash: routeHash });
      } else {
        if (this.$route.hash !== "")
          this.$router.push({ path: this.$route.path, hash: "" });
      }
    },
  },
  watch: {
    sortKeys() {
      this.updateHash();
    },
  },
};
</script>
