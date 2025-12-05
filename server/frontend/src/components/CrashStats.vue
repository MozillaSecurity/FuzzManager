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
      <template v-if="!restricted">
        <label for="id_no_toolfilter">Ignore Tool Filter</label>:
        <input
          id="id_no_toolfilter"
          v-model="ignoreToolFilter"
          type="checkbox"
          name="alltools"
          @change="fetch"
        /><br />
      </template>
    </div>
    <div class="panel-body">
      <crashstatsgraph :data="graphData" />
    </div>
    <div class="table-responsive">
      <table class="table table-condensed table-hover table-bordered table-db">
        <thead>
          <tr>
            <th
              :class="{
                active: sortKeys.includes('id') || sortKeys.includes('-id'),
              }"
              @click.exact="sortBy('id')"
              @click.ctrl.exact="addSort('id')"
            >
              Bucket
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('shortDescription') ||
                  sortKeys.includes('-shortDescription'),
              }"
              @click.exact="sortBy('shortDescription')"
              @click.ctrl.exact="addSort('shortDescription')"
            >
              Short Description
            </th>
            <th>Activity</th>
            <th
              :class="{
                active:
                  sortKeys.includes('counts[0]') ||
                  sortKeys.includes('-counts[0]'),
              }"
              @click.exact="sortBy('counts[0]')"
              @click.ctrl.exact="addSort('counts[0]')"
            >
              Reports (last hour)
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('counts[1]') ||
                  sortKeys.includes('-counts[1]'),
              }"
              @click.exact="sortBy('counts[1]')"
              @click.ctrl.exact="addSort('counts[1]')"
            >
              Reports (last day)
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('counts[2]') ||
                  sortKeys.includes('-counts[2]'),
              }"
              @click.exact="sortBy('counts[2]')"
              @click.ctrl.exact="addSort('counts[2]')"
            >
              Reports (last week)
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('bug__externalId') ||
                  sortKeys.includes('-bug__externalId'),
              }"
              @click.exact="sortBy('bug__externalId')"
              @click.ctrl.exact="addSort('bug__externalId')"
            >
              External Bug
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7">
              <div class="vl-parent">
                <loading
                  v-model:active="loading"
                  :can-cancel="false"
                  :is-full-page="true"
                />
              </div>
            </td>
          </tr>
          <tr
            v-for="signature of sortedSignatureData"
            v-else
            :key="signature.id"
          >
            <td>
              <a title="View signature" :href="signature.view_url">{{
                signature.id
              }}</a>
            </td>
            <td class="wrap-anywhere">
              <span class="two-line-limit">{{
                signature.shortDescription
              }}</span>
            </td>
            <td>
              <activitygraph
                :data="signature.crash_history"
                :range="activityRange"
              />
            </td>
            <td>{{ signature.counts[0] }}</td>
            <td>{{ signature.counts[1] }}</td>
            <td>{{ signature.counts[2] }}</td>
            <td>
              <a
                v-if="signature.bug && signature.bug_urltemplate"
                :class="{ fixedbug: signature.bug_closed }"
                :href="signature.bug_urltemplate"
                target="_blank"
              >
                {{ signature.bug }}
              </a>
              <p v-else-if="signature.bug">
                {{ signature.bug }} on {{ signature.bug_hostname }}
              </p>
              <assignbutton
                v-else
                :bucket="signature.id"
                :providers="providers"
              />
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
import { computed, defineComponent, getCurrentInstance, ref } from "vue";
import Loading from "vue-loading-overlay";

import "vue-loading-overlay/dist/css/index.css";
import * as api from "../api";
import { E_SERVER_ERROR, errorParser, multiSort, parseHash } from "../helpers";
import ActivityGraph from "./ActivityGraph.vue";
import CrashStatsGraph from "./CrashStatsGraph.vue";
import AssignBtn from "./Signatures/AssignBtn.vue";

export default defineComponent({
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
    crashstatsgraph: CrashStatsGraph,
    Loading,
  },
  mixins: [multiSort],
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    providers: {
      type: Array,
      required: true,
    },
    restricted: {
      type: Boolean,
      required: true,
    },
  },
  setup() {
    const instance = getCurrentInstance();

    const loading = ref(false);

    const defaultSortKeys = ["-counts[0]"];
    const validSortKeys = [
      "bug__externalId",
      "counts[0]",
      "counts[1]",
      "counts[2]",
      "id",
      "shortDescription",
    ];

    const graphData = ref({});
    const ignoreToolFilter = ref(false);
    const filterOS = ref("");
    const signatureData = ref([]);
    const sortKeys = ref([...defaultSortKeys]);
    const totals = ref([]);

    const sortedSignatureData = computed(() => {
      return instance.proxy.sortData(signatureData.value);
    });

    return {
      loading,
      defaultSortKeys,
      /*
       * outFilter: hits per hour (out of toolfilter)
       * inFilter: hits per hour (in toolfilter)
       */
      graphData,
      filterOS,
      ignoreToolFilter,
      // [Bucket()]
      signatureData,
      sortKeys,
      // [hour, day, week]
      totals,
      sortedSignatureData,
      validSortKeys,
    };
  },
  watch: {
    sortKeys() {
      this.updateHash();
    },
  },
  created() {
    if (this.$route.hash.startsWith("#")) {
      const hash = parseHash(this.$route.hash);
      this.ignoreToolFilter = hash.alltools === "1";
      this.filterOS = hash.os;
    }
    this.fetch();
  },
  methods: {
    // get stats
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.updateHash();
        try {
          // fetch stats

          const params = {
            ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
          };
          if (this.filterOS)
            params.query = JSON.stringify({
              op: "AND",
              os__name: this.filterOS,
            });
          const stats = await api.crashStats(params);

          // process result
          this.totals = stats.totals;
          this.graphData = {
            inFilter: stats.inFilterGraphData,
            outFilter: stats.outFilterGraphData,
          };

          // then get buckets for those stats
          if (Object.keys(stats.frequentBuckets).length) {
            const query = {
              op: "AND",
              id__in: Object.keys(stats.frequentBuckets),
            };
            if (this.filterOS) query.crashentry__os__name = this.filterOS;
            const signatureData = await api.listBuckets({
              vue: "1",
              ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
              query: JSON.stringify(query),
            });
            Object.keys(stats.frequentBuckets).forEach((x) =>
              signatureData.forEach((b) => {
                if (b.id == x) b.counts = stats.frequentBuckets[x];
              }),
            );
            this.signatureData = signatureData;
          } else {
            this.signatureData = [];
          }
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            swal("Oops", E_SERVER_ERROR, "error");
          } else {
            // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
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
    updateHash() {
      const hash = {};

      this.updateHashSort(hash);
      if (this.ignoreToolFilter) hash.alltools = "1";
      if (this.filterOS) hash.os = this.filterOS;
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
});
</script>

<style scoped>
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
</style>
