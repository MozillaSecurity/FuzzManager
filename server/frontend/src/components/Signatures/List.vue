<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-tag-fill"></i> Signatures</div>
    <div class="panel-body">
      <div>
        <div class="btn-group" role="group">
          <button type="button" class="btn btn-default" @click="updateShowAll">
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
            { name: 'bug', type: 'Integer (ID)' },
            { name: 'bug__closed', type: 'Date' },
            { name: 'bug__externalId', type: 'String' },
            { name: 'bug__externalType', type: 'Integer (ID)' },
            { name: 'bug__externalType__classname', type: 'String' },
            { name: 'bug__externalType__hostname', type: 'String' },
            { name: 'doNotReduce', type: 'Boolean' },
            { name: 'frequent', type: 'Boolean' },
            { name: 'optimizedSignature', type: 'String' },
            { name: 'permanent', type: 'Boolean' },
            { name: 'shortDescription', type: 'String' },
            { name: 'signature', type: 'String' },
          ]"
        />
        <textarea
          id="id_query"
          v-model="queryStr"
          class="form-control"
          name="query"
          spellcheck="false"
          :rows="(queryStr.match(/\n/g) || '').length + 1"
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
          v-model="ignoreToolFilter"
          type="checkbox"
          name="alltools"
        />
        <br />
        <button
          :disabled="!modified || loading"
          :title="queryButtonTitle"
          @click="fetch"
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
              :class="{
                active: sortKeys.includes('id') || sortKeys.includes('-id'),
              }"
              @click.exact="sortBy('id')"
              @click.ctrl.exact="addSort('id')"
            >
              ID
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
              Description
            </th>
            <th>Activity</th>
            <th
              :class="{
                active: sortKeys.includes('size') || sortKeys.includes('-size'),
              }"
              @click.exact="sortBy('size')"
              @click.ctrl.exact="addSort('size')"
            >
              Size
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('best_quality') ||
                  sortKeys.includes('-best_quality'),
              }"
              @click.exact="sortBy('best_quality')"
              @click.ctrl.exact="addSort('best_quality')"
            >
              Best Quality
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
            <th
              :class="{
                active:
                  sortKeys.includes('has_optimization') ||
                  sortKeys.includes('-has_optimization'),
              }"
              @click.exact="sortBy('has_optimization')"
              @click.ctrl.exact="addSort('has_optimization')"
            >
              Pending Optimization
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
          <Row
            v-for="signature in orderedSignatures"
            v-else
            :key="signature.id"
            :activity-range="activityRange"
            :providers="providers"
            :signature="signature"
          />
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import _isEqual from "lodash/isEqual";
import _throttle from "lodash/throttle";
import { defineComponent, ref } from "vue";
import Loading from "vue-loading-overlay";
import "vue-loading-overlay/dist/css/index.css";
import * as api from "../../api";
import { errorParser, multiSort, parseHash } from "../../helpers";
import HelpJSONQueryPopover from "../HelpJSONQueryPopover.vue";
import Row from "./Row.vue";

export default defineComponent({
  components: {
    Row,
    HelpJSONQueryPopover,
    Loading,
  },
  mixins: [multiSort],
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
  setup() {
    const loading = ref(false);
    const validSortKeys = [
      "best_quality",
      "bug__externalId",
      "has_optimization",
      "id",
      "shortDescription",
      "size",
    ];
    const defaultSortKeys = ["-id"];
    const ignoreToolFilter = ref(false);
    const queryError = ref("");
    const queryStr = ref(
      JSON.stringify({ op: "AND", bug__isnull: true }, null, 2),
    );
    const searchStr = ref("");
    const signatures = ref([]);
    const sortKeys = ref([...defaultSortKeys]);
    const totalEntries = ref("?");
    const modifiedCache = ref({
      ignoreToolFilter: false,
      queryStr: null,
    });

    return {
      loading,
      validSortKeys,
      defaultSortKeys,
      ignoreToolFilter,
      queryError,
      queryStr,
      searchStr,
      signatures,
      sortKeys,
      totalEntries,
      modifiedCache,
    };
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
      return this.sortData(this.signatures);
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
  watch: {
    sortKeys() {
      this.updateHash();
    },
  },
  created() {
    if (this.$route.query.all)
      this.queryStr = JSON.stringify({ op: "AND" }, null, 2);
    if (this.$route.query.ids)
      this.queryStr = JSON.stringify(
        { op: "AND", id__in: this.$route.query.ids.split(",") },
        null,
        2,
      );
    if (this.$route.hash.startsWith("#")) {
      const hash = parseHash(this.$route.hash);
      this.ignoreToolFilter = hash.alltools === "1";
      if (Object.prototype.hasOwnProperty.call(hash, "query")) {
        this.queryStr = JSON.stringify(JSON.parse(hash.query || ""), null, 2);
      }
    }
    this.updateHash();
    this.fetch();
  },
  methods: {
    updateShowAll() {
      if (this.showAll) {
        this.queryStr = JSON.stringify(
          Object.assign({ bug__isnull: true }, JSON.parse(this.queryStr)),
          null,
          2,
        );
      } else {
        const query = JSON.parse(this.queryStr);
        delete query["bug__isnull"];
        this.queryStr = JSON.stringify(query, null, 2);
      }
      this.fetch();
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
      { trailing: true },
    ),
    updateHash() {
      let hash = {};
      this.updateHashSort(hash);
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
});
</script>

<style scoped>
.m-strong {
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
</style>
