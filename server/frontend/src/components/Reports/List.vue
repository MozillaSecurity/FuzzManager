<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-card-list"></i> Reports</div>
    <div class="panel-body">
      <span v-if="advancedQuery">
        <label for="id_query">Search Query</label>
        <HelpJSONQueryPopover
          :parameters="[
            { name: 'id', type: 'Integer (ID)' },
            { name: 'reported_at', type: 'Date' },
            { name: 'os', type: 'Integer (ID)' },
            { name: 'os__name', type: 'String' },
            { name: 'bucket', type: 'Integer (ID)' },
            { name: 'bucket__signature', type: 'String' },
            { name: 'bucket__description', type: 'String' },
            { name: 'bucket__bug__external_id', type: 'String' },
          ]"
        />
        <textarea
          id="id_query"
          class="form-control"
          name="query"
          spellcheck="false"
          :rows="(advancedQueryStr.match(/\n/g) || '').length + 1"
          v-model="advancedQueryStr"
        ></textarea
        ><br />
        <pre
          v-if="advancedQueryError !== ''"
          class="alert alert-warning"
          role="alert"
          >{{ advancedQueryError }}</pre
        >
      </span>
      <span v-else>
        <label for="id_search">Search Text</label>:
        <input
          id="id_search"
          type="text"
          name="search"
          autocomplete="off"
          v-model="searchStr"
        /><br />
      </span>
      <span v-if="advancedQuery">
        <a
          title="Discard query and start over in simple mode"
          v-on:click="resetQueryToggleAdvanced"
          >Reset to simple search</a
        ><br />
      </span>
      <span v-else>
        <span v-for="(value, key) in filters" :key="key">
          {{ validFilters[key] }}:
          <span class="monospace">{{ value }}</span>
          <i v-on:click="removeFilter(key)" class="bi bi-x"></i><br />
        </span>
        <a
          title="Show the full query for the current search/filters"
          v-on:click="convertFiltersToAdvancedQuery"
          >Advanced query</a
        ><br />
      </span>
      <button
        v-on:click="fetch"
        :disabled="!modified || loading"
        :title="queryButtonTitle"
      >
        Query
      </button>
      <button
        v-if="canEdit"
        v-on:click="deleteQuery"
        :disabled="modified || loading || !haveResults"
        :title="deleteButtonTitle"
      >
        Delete
      </button>
    </div>
    <div class="panel-body">
      <p>
        <span v-if="deleteAsyncToken === null">
          Displaying {{ currentEntries }} /
        </span>
        <span v-else>Deleting</span>
        <span
          v-if="
            advancedQuery ||
            searchStr.trim() !== '' ||
            Object.keys(filters).length
          "
        >
          {{ totalEntries }} entries matching query.
        </span>
        <span v-else-if="watchId !== null && currentEntries">
          {{ totalEntries }} new entries in bucket {{ reports[0].bucket }}.
        </span>
        <span v-else>{{ totalEntries }} entries.</span>
      </p>

      <div class="pagination">
        <span class="step-links">
          <a
            v-on:click="prevPage"
            v-show="currentPage > 1"
            class="bi bi-caret-left-fill"
          ></a>
          <span class="current">
            Page {{ currentPage }} of {{ totalPages }}.
          </span>
          <a
            v-on:click="nextPage"
            v-show="currentPage < totalPages"
            data-toggle="tooltip"
            data-placement="top"
            title=""
            class="bi bi-caret-right-fill dimgray"
            data-original-title="Next"
          ></a>
        </span>
      </div>
    </div>
    <div class="table-responsive">
      <table
        class="table table-condensed table-hover table-bordered table-db wrap-none"
      >
        <thead>
          <tr>
            <th
              v-on:click.exact="sortBy('reported_at')"
              v-on:click.ctrl.exact="addSort('reported_at')"
              :class="{
                active:
                  sortKeys.includes('reported_at') ||
                  sortKeys.includes('-reported_at'),
              }"
            >
              Date Reported
            </th>
            <th
              v-on:click.exact="sortBy('uuid')"
              v-on:click.ctrl.exact="addSort('uuid')"
              :class="{
                active: sortKeys.includes('uuid') || sortKeys.includes('-uuid'),
              }"
            >
              UUID
            </th>
            <th
              v-on:click.exact="sortBy('bucket')"
              v-on:click.ctrl.exact="addSort('bucket')"
              :class="{
                active:
                  sortKeys.includes('bucket') || sortKeys.includes('-bucket'),
              }"
            >
              Bucket
            </th>
            <th
              v-on:click.exact="sortBy('url')"
              v-on:click.ctrl.exact="addSort('url')"
              :class="{
                active: sortKeys.includes('url') || sortKeys.includes('-url'),
              }"
            >
              URL
            </th>
            <th
              v-on:click.exact="sortBy('app__name')"
              v-on:click.ctrl.exact="addSort('app__name')"
              :class="{
                active:
                  sortKeys.includes('app__name') ||
                  sortKeys.includes('-app__name'),
              }"
            >
              App
            </th>
            <th
              v-on:click.exact="sortBy('app__channel')"
              v-on:click.ctrl.exact="addSort('app__channel')"
              :class="{
                active:
                  sortKeys.includes('app__channel') ||
                  sortKeys.includes('-app__channel'),
              }"
            >
              Channel
            </th>
            <th
              v-on:click.exact="sortBy('app__version')"
              v-on:click.ctrl.exact="addSort('app__version')"
              :class="{
                active:
                  sortKeys.includes('app__version') ||
                  sortKeys.includes('-app__version'),
              }"
            >
              Version
            </th>
            <th
              v-on:click.exact="sortBy('breakage_category__value')"
              v-on:click.ctrl.exact="addSort('breakage_category__value')"
              :class="{
                active:
                  sortKeys.includes('breakage_category__value') ||
                  sortKeys.includes('-breakage_category__value'),
              }"
            >
              Breakage Category
            </th>
            <th
              v-on:click.exact="sortBy('os__name')"
              v-on:click.ctrl.exact="addSort('os__name')"
              :class="{
                active:
                  sortKeys.includes('os__name') ||
                  sortKeys.includes('-os__name'),
              }"
            >
              OS
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="9">
              <ClipLoader class="m-strong" :color="'black'" :size="'50px'" />
            </td>
          </tr>
          <Row
            v-for="report in reports"
            :key="report.id"
            :report="report"
            v-on:add-filter="addFilter"
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
import swal from "sweetalert";
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
import Vue from "vue";
import {
  errorParser,
  E_SERVER_ERROR,
  multiSort,
  parseHash,
} from "../../helpers";
import * as api from "../../api";
import Row from "./Row.vue";
import HelpJSONQueryPopover from "../HelpJSONQueryPopover.vue";
import DeleteConfirmation from "./DeleteConfirmation.vue";

const pageSize = 100;
const validFilters = {
  app__channel: "Channel",
  app__name: "App",
  app__version: "Version",
  breakage_category__value: "Breakage Category",
  bucket: "Bucket",
  id: "ID",
  os__name: "OS",
  reported_at: "Date Reported",
  url: "URL",
  uuid: "UUID",
};

export default {
  mixins: [multiSort],
  components: {
    Row,
    ClipLoader,
    HelpJSONQueryPopover,
  },
  props: {
    canEdit: {
      type: Boolean,
      required: true,
    },
    watchId: {
      type: Number,
      required: false,
      default: null,
    },
  },
  data: function () {
    const defaultSortKeys = ["-id"];
    const validSortKeys = [
      "app__channel",
      "app__name",
      "app__version",
      "breakage_category__value",
      "bucket",
      "id",
      "os__name",
      "reported_at",
      "url",
      "uuid",
    ];
    return {
      advancedQuery: false,
      advancedQueryError: "",
      advancedQueryStr: "",
      cachedAdvancedQueryStr: null,
      cachedSearchStr: null,
      reports: null,
      currentEntries: "?",
      currentPage: 1,
      defaultSortKeys: defaultSortKeys,
      deleteAsyncTimer: null,
      deleteAsyncToken: null,
      filters: {},
      haveResults: false,
      loading: true,
      searchStr: "",
      sortKeys: [...defaultSortKeys],
      totalEntries: "?",
      totalPages: 1,
      validFilters: validFilters,
      validSortKeys: validSortKeys,
    };
  },
  created: function () {
    if (this.$route.query.q) this.searchStr = this.$route.query.q;
    if (this.$route.hash.startsWith("#")) {
      const hash = parseHash(this.$route.hash);
      if (Object.prototype.hasOwnProperty.call(hash, "page")) {
        try {
          this.currentPage = Number.parseInt(hash.page, 10);
        } catch (e) {
          // eslint-disable-next-line no-console
          console.debug(`parsing '#page=\\d+': ${e}`);
        }
      }
      if (Object.prototype.hasOwnProperty.call(hash, "bucket"))
        this.filters["bucket"] = hash.bucket;
      if (hash.advanced === "1") {
        this.advancedQuery = true;
        this.advancedQueryStr = JSON.stringify(
          JSON.parse(hash.query || ""),
          null,
          2,
        );
      } else {
        for (const filter of Object.keys(validFilters)) {
          if (Object.prototype.hasOwnProperty.call(hash, filter)) {
            this.filters[filter] = hash[filter];
          }
        }
      }
    }
    this.fetch();
  },
  computed: {
    modified() {
      if (this.advancedQuery) {
        const queryStr = (() => {
          try {
            return JSON.parse(this.advancedQueryStr);
          } catch (e) {} // eslint-disable-line no-empty
        })();
        if (!_isEqual(queryStr, this.cachedAdvancedQueryStr)) {
          // eslint-disable-next-line no-console
          console.debug("modified because query differs (advanced)");
          return true;
        } else {
          // eslint-disable-next-line no-console
          console.debug("not modified (advanced)");
          return false;
        }
      }
      if (this.searchStr.trim() !== this.cachedSearchStr) {
        // eslint-disable-next-line no-console
        console.debug("modified because query differs (basic)");
        return true;
      }
      // eslint-disable-next-line no-console
      console.debug("not modified (basic)");
      return false;
    },
    deleteButtonTitle() {
      if (!this.haveResults) return "No results";
      if (this.loading) return "Operation in progress";
      if (this.modified) return "Query is modified";
      return "Delete reports matching current query";
    },
    queryButtonTitle() {
      if (this.loading) return "Operation in progress";
      if (!this.modified) return "Results match current query";
      return "Submit query";
    },
  },
  methods: {
    addFilter: function (key, value) {
      this.filters[key] = value;
      this.fetch();
    },
    buildCommonParams() {
      return {
        query: this.advancedQuery
          ? this.advancedQueryStr
          : JSON.stringify(this.buildSimpleQuery()),
        watch: this.watchId === null ? false : this.watchId,
      };
    },
    buildDeleteParams() {
      const result = this.buildCommonParams();
      result.query = JSON.stringify({
        op: "AND",
        _: JSON.parse(result.query),
        id__lte: this.latestEntryID,
      });
      return result;
    },
    buildQueryParams() {
      const result = this.buildCommonParams();
      result.vue = "1";
      result.limit = pageSize;
      result.offset = `${(this.currentPage - 1) * pageSize}`;
      result.ordering = this.sortKeys.join();
      return result;
    },
    updateModifiedCache() {
      // eslint-disable-next-line no-console
      console.debug("update modified cache");
      try {
        // ignore query errors
        this.cachedAdvancedQueryStr = JSON.parse(this.advancedQueryStr);
      } catch (e) {} // eslint-disable-line no-empty
      this.cachedSearchStr = this.searchStr.trim();
    },
    buildSimpleQuery: function () {
      let query = Object.assign({ op: "AND" }, this.filters);
      const searchStr = this.searchStr.trim();
      if (searchStr !== "") {
        query["_search"] = {
          op: "OR",
          shortSignature__contains: searchStr,
          rawStderr__contains: searchStr,
          rawReportData__contains: searchStr,
          args__contains: searchStr,
        };
      }
      return query;
    },
    convertFiltersToAdvancedQuery: function () {
      this.advancedQuery = true;
      this.advancedQueryStr = JSON.stringify(this.buildSimpleQuery(), null, 2);
      this.searchStr = "";
      this.filters = {};
      const hash = parseHash(this.$route.hash);
      if (Object.prototype.hasOwnProperty.call(hash, "bucket"))
        this.filters["bucket"] = hash.bucket;
      this.updateHash();
    },
    deleteQuery: async function () {
      // - show confirmation modal with affected report count
      const FormCtor = Vue.extend(DeleteConfirmation);
      const deleteConfirmForm = new FormCtor({
        parent: this,
        propsData: {
          reportCount: this.totalEntries,
        },
      }).$mount();
      const value = await swal({
        title: "Delete these reports?",
        content: deleteConfirmForm.$el,
        buttons: true,
      });
      if (value) {
        // - if confirmed, submit delete and get async token
        this.loading = true;
        try {
          this.deleteAsyncToken = await api.deleteReports(
            this.buildDeleteParams(),
          );
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            if (this.advancedQuery) {
              this.advancedQueryError = err.response.data.detail;
            } else {
              // eslint-disable-next-line no-console
              console.debug(err.response.data);
              swal("Oops", E_SERVER_ERROR, "error");
            }
            this.loading = false;
          } else {
            // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
            // eslint-disable-next-line no-console
            console.debug(errorParser(err));
            this.$router.go(0);
            return;
          }
        }
        // - start timer loop to poll token
        this.deleteAsyncTimer = setTimeout(this.pollDeleteDone, 1000);
      }
    },
    pollDeleteDone: async function () {
      this.deleteAsyncTimer = null;
      let deleteDone;
      try {
        deleteDone = await api.pollAsyncOp(this.deleteAsyncToken);
      } catch (err) {
        // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
        // eslint-disable-next-line no-console
        console.debug(errorParser(err));
        this.$router.go(0);
        return;
      }
      if (deleteDone) {
        this.deleteAsyncToken = null;
        this.fetch();
      } else {
        this.deleteAsyncTimer = setTimeout(this.pollDeleteDone, 1000);
      }
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.updateModifiedCache();
        this.reports = null;
        this.advancedQueryError = "";
        try {
          const data = await api.listReports(this.buildQueryParams());
          this.reports = data.results;
          this.latestEntryID = data.latest_entry_id;
          this.currentEntries = this.reports.length;
          this.totalEntries = data.count;
          this.haveResults = data.count > 0 ? true : false;
          this.totalPages = Math.max(
            Math.ceil(this.totalEntries / pageSize),
            1,
          );
          if (this.currentPage > this.totalPages) {
            this.currentPage = this.totalPages;
            this.fetch();
            return;
          }
          this.updateHash();
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            if (this.advancedQuery) {
              this.advancedQueryError = err.response.data.detail;
            } else {
              // eslint-disable-next-line no-console
              console.debug(err.response.data);
              swal("Oops", E_SERVER_ERROR, "error");
            }
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
    nextPage: function () {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.fetch();
      }
    },
    prevPage: function () {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetch();
      }
    },
    removeFilter: function (key) {
      if (Object.prototype.hasOwnProperty.call(this.filters, key)) {
        delete this.filters[key];
        this.fetch();
      }
    },
    resetQueryToggleAdvanced: function () {
      this.advancedQuery = false;
      this.advancedQueryStr = "";
      this.searchStr = "";
      this.filters = {};
      const hash = parseHash(this.$route.hash);
      if (Object.prototype.hasOwnProperty.call(hash, "bucket"))
        this.filters["bucket"] = hash.bucket;
      this.fetch();
    },
    updateHash: function () {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
      this.updateHashSort(hash);
      if (this.filters["bucket"] !== undefined)
        hash.bucket = this.filters["bucket"];
      if (this.advancedQuery) {
        hash.advanced = "1";
        hash.query = encodeURIComponent(this.advancedQueryStr);
      } else {
        if (this.searchStr.trim() !== "")
          hash.search = encodeURIComponent(this.searchStr.trim());
        for (const [key, value] of Object.entries(this.filters))
          hash[key] = encodeURIComponent(value);
      }
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
  beforeDestroy() {
    if (this.deleteAsyncTimer !== null) clearTimeout(this.deleteAsyncTimer);
  },
  watch: {
    sortKeys() {
      this.fetch();
    },
  },
};
</script>

<style scoped>
.dimgray {
  color: dimgray;
}
.monospace {
  font-family: monospace;
}
.m-strong {
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
}
</style>
