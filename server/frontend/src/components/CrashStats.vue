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
          type="checkbox"
          name="alltools"
          v-model="ignoreToolFilter"
          v-on:change="fetch"
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
              v-on:click.exact="sortBy('id')"
              v-on:click.ctrl.exact="addSort('id')"
              :class="{
                active: sortKeys.includes('id') || sortKeys.includes('-id'),
              }"
            >
              Bucket
            </th>
            <th
              v-on:click.exact="sortBy('shortDescription')"
              v-on:click.ctrl.exact="addSort('shortDescription')"
              :class="{
                active:
                  sortKeys.includes('shortDescription') ||
                  sortKeys.includes('-shortDescription'),
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
              v-on:click.exact="sortBy('bug__externalId')"
              v-on:click.ctrl.exact="addSort('bug__externalId')"
              :class="{
                active:
                  sortKeys.includes('bug__externalId') ||
                  sortKeys.includes('-bug__externalId'),
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
          <tr
            v-else
            v-for="signature of sortedSignatureData"
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
import _orderBy from "lodash/orderBy";
import swal from "sweetalert";
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
import { errorParser, E_SERVER_ERROR, parseHash } from "../helpers";
import * as api from "../api";
import AssignBtn from "./Signatures/AssignBtn.vue";
import ActivityGraph from "./ActivityGraph.vue";
import CrashStatsGraph from "./CrashStatsGraph.vue";

const validSortKeys = [
  "id",
  "shortDescription",
  "counts[0]",
  "counts[1]",
  "counts[2]",
  "bug__externalId",
];
const defaultSortKey = "-counts[0]";

export default {
  components: {
    ClipLoader,
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
    crashstatsgraph: CrashStatsGraph,
  },
  data: () => ({
    // [hour, day, week]
    totals: [],
    // [Bucket()]
    signatureData: [],
    /*
     * outFilter: hits per hour (out of toolfilter)
     * inFilter: hits per hour (in toolfilter)
     */
    graphData: {},
    sortKeys: [defaultSortKey],
    ignoreToolFilter: false,
    loading: false,
  }),
  created: function () {
    if (this.$route.hash.startsWith("#")) {
      const hash = parseHash(this.$route.hash);
      if (Object.prototype.hasOwnProperty.call(hash, "sort")) {
        const sortKeys = hash.sort.split(",").filter((key) => {
          const realKey = key.startsWith("-") ? key.substring(1) : key;
          if (validSortKeys.includes(realKey)) {
            return true;
          }
          // eslint-disable-next-line no-console
          console.debug(`parsing '#sort=\\s+': unrecognized key '${realKey}'`);
          return false;
        });
        if (sortKeys.length > 0) {
          this.sortKeys = sortKeys;
        }
      }
      this.ignoreToolFilter = hash.alltools === "1";
    }
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
    restricted: {
      type: Boolean,
      required: true,
    },
  },
  computed: {
    sortedSignatureData: function () {
      return _orderBy(
        this.signatureData,
        this.sortKeys.map((key) =>
          key.startsWith("-") ? key.substring(1) : key
        ),
        this.sortKeys.map((key) => (key.startsWith("-") ? "desc" : "asc"))
      );
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
          const stats = await api.crashStats({
            ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
          });

          // process result
          this.totals = stats.totals;
          this.graphData = {
            inFilter: stats.inFilterGraphData,
            outFilter: stats.outFilterGraphData,
          };

          // then get buckets for those stats
          if (Object.keys(stats.frequentBuckets).length) {
            const signatureData = await api.listBuckets({
              vue: "1",
              ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
              query: JSON.stringify({
                op: "AND",
                id__in: Object.keys(stats.frequentBuckets),
              }),
            });
            Object.keys(stats.frequentBuckets).forEach((x) =>
              signatureData.forEach((b) => {
                if (b.id == x) b.counts = stats.frequentBuckets[x];
              })
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
      { trailing: true }
    ),
    addSort: function (sortKey) {
      /*
       * add sort by sortKey to existing sort keys
       * if already sorting, by sortKey,
       *   reverse the sort order without changing the priority of sort keys
       * if not sorting by sortKey yet,
       *   sort first by this sortKey and then by existing sort keys
       */
      const index = this.sortKeys.indexOf(sortKey);
      if (index >= 0) {
        this.sortKeys[index] = `-${sortKey}`;
      } else {
        const revIndex = this.sortKeys.indexOf(`-${sortKey}`);
        if (revIndex >= 0) {
          this.sortKeys[revIndex] = sortKey;
        } else {
          this.sortKeys.unshift(sortKey);
        }
      }
      this.updateHash();
    },
    sortBy: function (sortKey) {
      /*
       * reset sort by sortKey
       * if the display is already sorted by sortKey (alone or in concert),
       *   then reverse the sort order, but always remove other sort keys
       */
      if (this.sortKeys.includes(sortKey)) {
        this.sortKeys = [`-${sortKey}`];
      } else if (this.sortKeys.includes(`-${sortKey}`)) {
        this.sortKeys = [sortKey];
      } else {
        this.sortKeys = [sortKey];
      }
      this.updateHash();
    },
    updateHash: function () {
      const hash = {};
      if (this.sortKeys.length !== 1 || this.sortKeys[0] !== defaultSortKey) {
        hash.sort = this.sortKeys.join();
      }
      if (this.ignoreToolFilter) hash.alltools = "1";
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
};
</script>
