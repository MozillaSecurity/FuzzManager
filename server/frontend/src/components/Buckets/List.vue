<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-tag-fill"></i> Buckets</div>
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
            { name: 'bug__external_id', type: 'String' },
            { name: 'bug__external_type', type: 'Integer (ID)' },
            { name: 'bug__external_type__classname', type: 'String' },
            { name: 'bug__external_type__hostname', type: 'String' },
            { name: 'short_description', type: 'String' },
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
        Displaying {{ totalEntries }} of all buckets in the database.
      </p>
      <p v-else>
        Displaying {{ totalEntries }} unreported buckets from the database.
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
              v-on:click.exact="sortBy('short_description')"
              v-on:click.ctrl.exact="addSort('short_description')"
              :class="{
                active:
                  sortKeys.includes('short_description') ||
                  sortKeys.includes('-short_description'),
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
            v-for="bucket in orderedBuckets"
            :activity-range="activityRange"
            :key="bucket.id"
            :providers="providers"
            :bucket="bucket"
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
    providers: {
      type: Array,
      required: true,
    },
  },
  data: function () {
    const validSortKeys = [
      "best_quality",
      "bug__external_id",
      "has_optimization",
      "id",
      "short_description",
      "size",
    ];
    const defaultSortKeys = ["-id"];
    return {
      defaultSortKeys: defaultSortKeys,
      loading: false,
      modifiedCache: {},
      queryError: "",
      queryStr: JSON.stringify({ op: "AND", bug__isnull: true }, null, 2),
      searchStr: "",
      buckets: [],
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
      if (Object.prototype.hasOwnProperty.call(hash, "query")) {
        this.queryStr = JSON.stringify(JSON.parse(hash.query || ""), null, 2);
      }
    }
    this.updateHash();
    this.fetch();
  },
  computed: {
    modified() {
      const queryStr = (() => {
        try {
          return JSON.parse(this.queryStr);
        } catch (e) {} // eslint-disable-line no-empty
      })();
      return !_isEqual(queryStr, this.modifiedCache.queryStr);
    },
    orderedBuckets() {
      return this.sortData(this.buckets);
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
    buildParams() {
      return {
        vue: "1",
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
        this.buckets = null;
        this.queryError = "";
        try {
          const data = await api.listBuckets(this.buildParams());
          this.buckets = data;
          this.totalEntries = this.buckets.length;
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
