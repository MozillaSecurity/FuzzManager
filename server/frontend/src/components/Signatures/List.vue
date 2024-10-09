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
            :loading-quality="loadingQuality"
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
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
import { errorParser, multiSort, parseHash } from "../../helpers";
import * as api from "../../api";
import Row from "./Row.vue";
import HelpJSONQueryPopover from "../HelpJSONQueryPopover.vue";

export default {
  mixins: [multiSort],
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
  data: function () {
    const validSortKeys = [
      "best_quality",
      "bug__externalId",
      "has_optimization",
      "id",
      "shortDescription",
      "size",
    ];
    const defaultSortKeys = ["-id"];
    return {
      defaultSortKeys: defaultSortKeys,
      ignoreToolFilter: false,
      loading: false,
      loadingQuality: false,
      modifiedCache: {},
      queryError: "",
      queryStr: JSON.stringify({ op: "AND", bug__isnull: true }, null, 2),
      searchStr: "",
      signatures: [],
      sortKeys: [...defaultSortKeys],
      totalEntries: "?",
      validSortKeys: validSortKeys,
    };
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
    buildParams(loadQuality) {
      return {
        vue: "1",
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
        include_quality: loadQuality ? "1" : "0",
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
        this.loadingQuality = true;
        this.updateModifiedCache();
        this.signatures = null;
        this.queryError = "";
        // Load list first without (expensive) testcase quality
        try {
          const data = await api.listBuckets(this.buildParams(false));
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
        // If we got any signatures, reload this time with testcase quality
        if (this.signatures.length) {
          try {
            const data = await api.listBuckets(this.buildParams(true));
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
        }
        this.loadingQuality = false;
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
