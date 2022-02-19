<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-tag-fill"></i> Signatures</div>
    <div class="panel-body">
      <div>
        <div class="btn-group" role="group">
          <button
            type="button"
            class="btn btn-default"
            v-on:click="updateShowAll"
          >
            {{ showAll ? "View Unassigned" : "View All" }}
          </button>
          <a :href="watchUrl" class="btn btn-default">View Watched</a>
        </div>
      </div>
      <br />
      <div>
        <label for="id_query">Search Query</label>
        <HelpJSONQueryPopover
          :parameters="[
            { name: 'id', type: 'Integer (ID)' },
            { name: 'signature', type: 'String' },
            { name: 'optimizedSignature', type: 'String' },
            { name: 'shortDescription', type: 'String' },
            { name: 'frequent', type: 'Boolean' },
            { name: 'permanent', type: 'Boolean' },
            { name: 'bug', type: 'Integer (ID)' },
            { name: 'bug__externalId', type: 'String' },
            { name: 'bug__closed', type: 'Date' },
            { name: 'bug__externalType', type: 'Integer (ID)' },
            { name: 'bug__externalType__classname', type: 'String' },
            { name: 'bug__externalType__hostname', type: 'String' },
          ]"
        />
        <textarea
          id="id_query"
          class="form-control"
          name="query"
          spellcheck="false"
          :rows="(queryStr.match(/\n/g) || '').length + 1"
          v-model="queryStr"
        ></textarea>
        <br />
        <div v-if="queryError" class="alert alert-warning" role="alert">
          {{ queryError }}
        </div>
      </div>
      <div>
        <label for="id_no_toolfilter">Ignore Tool Filter</label>:
        <input
          id="id_no_toolfilter"
          type="checkbox"
          name="alltools"
          v-model="ignoreToolFilter"
        />
        <br />
        <button
          v-on:click="fetch"
          :disabled="!modified || loading"
          :title="queryButtonTitle"
        >
          Query
        </button>
      </div>
      <br />
      <p v-if="showAll">
        Displaying {{ totalEntries }} of all signature entries in the database.
      </p>
      <p v-else>
        Displaying {{ totalEntries }} unreported signature entries from the
        database.
      </p>
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
              ID
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
              Description
            </th>
            <th>Activity</th>
            <th
              v-on:click.exact="sortBy('size')"
              v-on:click.ctrl.exact="addSort('size')"
              :class="{
                active: sortKeys.includes('size') || sortKeys.includes('-size'),
              }"
            >
              Size
            </th>
            <th
              v-on:click.exact="sortBy('best_quality')"
              v-on:click.ctrl.exact="addSort('best_quality')"
              :class="{
                active:
                  sortKeys.includes('best_quality') ||
                  sortKeys.includes('-best_quality'),
              }"
            >
              Best Quality
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
            <th
              v-on:click.exact="sortBy('has_optimization')"
              v-on:click.ctrl.exact="addSort('has_optimization')"
              :class="{
                active:
                  sortKeys.includes('has_optimization') ||
                  sortKeys.includes('-has_optimization'),
              }"
            >
              Pending Optimization
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7">
              <ClipLoader class="m-strong" :color="'black'" :size="'50px'" />
            </td>
          </tr>
          <Row
            v-for="signature in orderedSignatures"
            :activity-range="activityRange"
            :key="signature.id"
            :providers="providers"
            :signature="signature"
            v-else
          />
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import _throttle from "lodash/throttle";
import _isEqual from "lodash/isEqual";
import _orderBy from "lodash/orderBy";
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
import { errorParser, parseHash } from "../../helpers";
import * as api from "../../api";
import Row from "./Row.vue";
import HelpJSONQueryPopover from "../HelpJSONQueryPopover.vue";

const validSortKeys = [
  "id",
  "shortDescription",
  "size",
  "best_quality",
  "has_optimization",
  "bug__externalId",
];
const defaultSortKey = "-id";

export default {
  components: {
    Row,
    ClipLoader,
    HelpJSONQueryPopover,
  },
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    watchUrl: {
      type: String,
      required: true,
    },
    providers: {
      type: Array,
      required: true,
    },
  },
  data: () => ({
    modifiedCache: {},
    signatures: [],
    sortKeys: [defaultSortKey],
    queryStr: JSON.stringify({ op: "AND", bug__isnull: true }, null, 2),
    queryError: "",
    ignoreToolFilter: false,
    searchStr: "",
    totalEntries: "?",
    loading: false,
  }),
  created() {
    if (this.$route.query.all)
      this.queryStr = JSON.stringify({ op: "AND" }, null, 2);
    if (this.$route.query.ids)
      this.queryStr = JSON.stringify(
        { op: "AND", id__in: this.$route.query.ids.split(",") },
        null,
        2
      );
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
      if (Object.prototype.hasOwnProperty.call(hash, "query")) {
        this.queryStr = JSON.stringify(JSON.parse(hash.query || ""), null, 2);
      }
    }
    this.updateHash();
    this.fetch();
  },
  computed: {
    modified() {
      if (this.ignoreToolFilter !== this.modifiedCache.ignoreToolFilter)
        return true;
      const queryStr = (() => {
        try {
          return JSON.parse(this.queryStr);
        } catch (e) {} // eslint-disable-line no-empty
      })();
      return !_isEqual(queryStr, this.modifiedCache.queryStr);
    },
    orderedSignatures() {
      const realKeys = [];
      const orders = [];

      this.sortKeys.forEach((key) => {
        realKeys.push(key.startsWith("-") ? key.substring(1) : key);
        orders.push(key.startsWith("-") ? "desc" : "asc");
      });
      return _orderBy(this.signatures, realKeys, orders);
    },
    queryButtonTitle() {
      if (this.loading) return "Query in progress";
      if (!this.modified) return "Results match current query";
      return "Submit query";
    },
    showAll() {
      return !this.queryStr.includes('"bug__isnull": true');
    },
  },
  methods: {
    updateShowAll() {
      if (this.showAll) {
        this.queryStr = JSON.stringify(
          Object.assign({ bug__isnull: true }, JSON.parse(this.queryStr)),
          null,
          2
        );
      } else {
        const query = JSON.parse(this.queryStr);
        delete query["bug__isnull"];
        this.queryStr = JSON.stringify(query, null, 2);
      }
      this.fetch();
    },
    addSort(sortKey) {
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
          this.sortKeys.unshift(`-${sortKey}`);
        }
      }
    },
    sortBy(sortKey) {
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
        this.sortKeys = [`-${sortKey}`];
      }
    },
    buildParams() {
      return {
        vue: "1",
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
        query: this.queryStr,
      };
    },
    updateModifiedCache() {
      this.modifiedCache.ignoreToolFilter = this.ignoreToolFilter;
      try {
        // ignore query errors
        this.modifiedCache.queryStr = JSON.parse(this.queryStr);
      } catch (e) {} // eslint-disable-line no-empty
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.updateModifiedCache();
        this.signatures = null;
        this.queryError = "";
        try {
          const data = await api.listBuckets(this.buildParams());
          this.signatures = data;
          this.totalEntries = this.signatures.length;
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            this.queryError = err.response.data.detail;
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
    updateHash() {
      let hash = {};
      if (this.sortKeys.length !== 1 || this.sortKeys[0] !== defaultSortKey) {
        hash.sort = this.sortKeys.join();
      }
      if (this.queryStr) hash.query = encodeURIComponent(this.queryStr);
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
  watch: {
    sortKeys() {
      this.updateHash();
    },
  },
};
</script>

<style scoped>
.m-strong {
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
}
</style>
