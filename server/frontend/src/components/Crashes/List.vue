<template>
  <div class="panel panel-default">
    <div class="panel-heading"><i class="bi bi-card-list"></i> Crashes</div>
    <div class="panel-body">
      <span v-if="advancedQuery">
        <label for="id_query">Search Query</label>
        <HelpJSONQueryPopover
          :parameters="[
            { name: 'id', type: 'Integer (ID)' },
            { name: 'created', type: 'Date' },
            { name: 'tool', type: 'Integer (ID)' },
            { name: 'tool__name', type: 'String' },
            { name: 'platform', type: 'Integer (ID)' },
            { name: 'platform__name', type: 'String' },
            { name: 'product', type: 'Integer (ID)' },
            { name: 'product__name', type: 'String' },
            { name: 'os', type: 'Integer (ID)' },
            { name: 'os__name', type: 'String' },
            { name: 'testcase', type: 'Integer (ID)' },
            { name: 'testcase__test', type: 'String' },
            { name: 'testcase__quality', type: 'Integer' },
            { name: 'bucket', type: 'Integer (ID)' },
            { name: 'bucket__signature', type: 'String' },
            { name: 'bucket__shortDescription', type: 'String' },
            { name: 'bucket__bug__externalId', type: 'String' },
            { name: 'rawStdout', type: 'String' },
            { name: 'rawStderr', type: 'String' },
            { name: 'rawCrashData', type: 'String' },
            { name: 'metadata', type: 'String' },
            { name: 'env', type: 'String' },
            { name: 'args', type: 'String' },
            { name: 'crashAddress', type: 'String' },
            { name: 'shortSignature', type: 'String' },
          ]"
        />
        <textarea
          id="id_query"
          v-model="advancedQueryStr"
          class="form-control"
          name="query"
          spellcheck="false"
          :rows="(advancedQueryStr.match(/\n/g) || '').length + 1"
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
          v-model="searchStr"
          type="text"
          name="search"
          autocomplete="off"
        /><br />
        <label for="id_bucketed">Include Bucketed</label>:
        <input
          id="id_bucketed"
          v-model="showBucketed"
          type="checkbox"
          name="bucketed"
          :disabled="!canUnshowBucketed"
        /><br />
      </span>
      <template v-if="!restricted">
        <label for="id_no_toolfilter">Ignore Tool Filter</label>:
        <input
          id="id_no_toolfilter"
          v-model="ignoreToolFilter"
          type="checkbox"
          name="alltools"
        /><br />
      </template>
      <span v-if="advancedQuery">
        <a
          title="Discard query and start over in simple mode"
          @click="resetQueryToggleAdvanced"
          >Reset to simple search</a
        ><br />
      </span>
      <span v-else>
        <span v-for="(value, key) in filters" :key="key">
          {{ validFilters[key] }}:
          <span class="monospace">{{ value }}</span>
          <i class="bi bi-x" @click="removeFilter(key)"></i><br />
        </span>
        <a
          title="Show the full query for the current search/filters"
          @click="convertFiltersToAdvancedQuery"
          >Advanced query</a
        ><br />
      </span>
      <!--   -->
      <button
        :disabled="!modified || loading"
        :title="queryButtonTitle"
        @click="fetch"
      >
        Query
      </button>
      <button
        :disabled="modified || loading || !haveResults"
        :title="deleteButtonTitle"
        @click="deleteQuery"
      >
        Delete
      </button>
    </div>
    <div class="panel-body">
      <p>
        <span v-if="deletedEntries === null">
          Displaying {{ currentEntries }} /
        </span>
        <span v-else>Deleted ({{ deletedEntries }} / {{ deleteTotal }})</span>
        <span
          v-if="
            advancedQuery ||
            searchStr.trim() !== '' ||
            Object.keys(filters).length
          "
        >
          {{ totalEntries }} entries matching query.
        </span>
        <span v-else-if="!showBucketed">
          {{ totalEntries }} unbucketed entries.
        </span>
        <span v-else-if="watchId !== null && crashes">
          {{ totalEntries }} new entries in bucket {{ crashes[0].bucket }}.
        </span>
        <span v-else>{{ totalEntries }} entries.</span>
      </p>

      <div class="pagination">
        <span class="step-links">
          <a
            v-show="currentPage > 1"
            class="bi bi-caret-left-fill"
            @click="prevPage"
          ></a>
          <span class="current">
            Page {{ currentPage }} of {{ totalPages }}.
          </span>
          <a
            v-show="currentPage < totalPages"
            data-toggle="tooltip"
            data-placement="top"
            title=""
            class="bi bi-caret-right-fill dimgray"
            data-original-title="Next"
            @click="nextPage"
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
                  sortKeys.includes('created') || sortKeys.includes('-created'),
              }"
              @click.exact="sortBy('created')"
              @click.ctrl.exact="addSort('created')"
            >
              Date Added
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('bucket') || sortKeys.includes('-bucket'),
              }"
              @click.exact="sortBy('bucket')"
              @click.ctrl.exact="addSort('bucket')"
            >
              Bucket
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('shortSignature') ||
                  sortKeys.includes('-shortSignature'),
              }"
              @click.exact="sortBy('shortSignature')"
              @click.ctrl.exact="addSort('shortSignature')"
            >
              Short Signature
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('crashAddress') ||
                  sortKeys.includes('-crashAddress'),
              }"
              @click.exact="sortBy('crashAddress')"
              @click.ctrl.exact="addSort('crashAddress')"
            >
              Crash Address
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('testcase__size') ||
                  sortKeys.includes('-testcase__size'),
              }"
              @click.exact="sortBy('testcase__size')"
              @click.ctrl.exact="addSort('testcase__size')"
            >
              Test Size
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('testcase__quality') ||
                  sortKeys.includes('-testcase__quality'),
              }"
              @click.exact="sortBy('testcase__quality')"
              @click.ctrl.exact="addSort('testcase__quality')"
            >
              Test Info
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('product__name') ||
                  sortKeys.includes('-product__name'),
              }"
              @click.exact="sortBy('product__name')"
              @click.ctrl.exact="addSort('product__name')"
            >
              Product
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('product__version') ||
                  sortKeys.includes('-product__version'),
              }"
              @click.exact="sortBy('product__version')"
              @click.ctrl.exact="addSort('product__version')"
            >
              Version
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('platform__name') ||
                  sortKeys.includes('-platform__name'),
              }"
              @click.exact="sortBy('platform__name')"
              @click.ctrl.exact="addSort('platform__name')"
            >
              Platform
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('os__name') ||
                  sortKeys.includes('-os__name'),
              }"
              @click.exact="sortBy('os__name')"
              @click.ctrl.exact="addSort('os__name')"
            >
              OS
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('tool__name') ||
                  sortKeys.includes('-tool__name'),
              }"
              @click.exact="sortBy('tool__name')"
              @click.ctrl.exact="addSort('tool__name')"
            >
              Tool
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="11">
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
            v-for="crash in crashes"
            v-else
            :key="crash.id"
            :crash="crash"
            @add-filter="addFilter"
          />
        </tbody>
      </table>
    </div>
    <div v-show="totalPages > 1" class="panel-body">
      <div class="pagination">
        <span class="step-links">
          <a
            v-show="currentPage > 1"
            class="bi bi-caret-left-fill"
            @click="prevPage"
          ></a>
          <span class="current">
            Page {{ currentPage }} of {{ totalPages }}.
          </span>
          <a
            v-show="currentPage < totalPages"
            data-toggle="tooltip"
            data-placement="top"
            title=""
            class="bi bi-caret-right-fill dimgray"
            data-original-title="Next"
            @click="nextPage"
          ></a>
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import _isEqual from "lodash/isEqual";
import _throttle from "lodash/throttle";
import swal from "sweetalert";
import { createVNode, defineComponent, getCurrentInstance, render } from "vue";
import Loading from "vue-loading-overlay";
import "vue-loading-overlay/dist/css/index.css";
import * as api from "../../api";
import {
  E_SERVER_ERROR,
  errorParser,
  multiSort,
  parseHash,
} from "../../helpers";
import HelpJSONQueryPopover from "../HelpJSONQueryPopover.vue";
import DeleteConfirmation from "./DeleteConfirmation.vue";
import Row from "./Row.vue";

const pageSize = 100;
const validFilters = {
  bucket: "Bucket",
  client__name: "Client name",
  client__name__contains: "Client name (sub-string match)",
  os__name: "OS",
  platform__name: "Platform",
  product__name: "Product",
  product__version: "Version",
  testcase__quality: "Testcase Quality",
  testcase__quality__gt: "Testcase Quality (greater than)",
  testcase__quality__lt: "Testcase Quality (lesser than)",
  testcase__size__gt: "Testcase Size (greater than)",
  testcase__size__lt: "Testcase Size (lesser than)",
  testcase__size: "Testcase Size",
  tool__name: "Tool",
  tool__name__contains: "Tool (sub-string match)",
};

export default defineComponent({
  components: {
    Row,
    HelpJSONQueryPopover,
    Loading,
  },
  mixins: [multiSort],
  props: {
    restricted: {
      type: Boolean,
      required: true,
    },
    watchId: {
      type: Number,
      required: false,
      default: null,
    },
  },
  data() {
    const defaultSortKeys = ["-id"];
    const validSortKeys = [
      "bucket",
      "crashAddress",
      "created",
      "id",
      "os__name",
      "platform__name",
      "product__name",
      "product__version",
      "shortSignature",
      "testcase__quality",
      "testcase__size",
      "tool__name",
    ];
    return {
      advancedQuery: false,
      advancedQueryError: "",
      advancedQueryStr: "",
      cachedAdvancedQueryStr: null,
      cachedIgnoreToolFilter: null,
      cachedSearchStr: null,
      cachedShowBucketed: null,
      canUnshowBucketed: true,
      crashes: null,
      currentEntries: "?",
      currentPage: 1,
      defaultSortKeys: defaultSortKeys,
      deletedEntries: null,
      deleteTotal: null,
      filters: {},
      haveResults: false,
      ignoreToolFilter: false,
      searchStr: "",
      showBucketed: false,
      sortKeys: [...defaultSortKeys],
      totalEntries: "?",
      totalPages: 1,
      validFilters: validFilters,
      validSortKeys: validSortKeys,
      loading: false,
      count: 0,
    };
  },
  computed: {
    modified() {
      if (this.ignoreToolFilter !== this.cachedIgnoreToolFilter) {
        // eslint-disable-next-line no-console
        console.debug("modified because toolfilter differs");
        return true;
      }
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
      if (this.showBucketed !== this.cachedShowBucketed) {
        // eslint-disable-next-line no-console
        console.debug("modified because show_bucketed differs (basic)");
        return true;
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
      return "Delete crashes matching current query";
    },
    queryButtonTitle() {
      if (this.loading) return "Operation in progress";
      if (!this.modified) return "Results match current query";
      return "Submit query";
    },
  },
  watch: {
    sortKeys() {
      this.fetch();
    },
  },
  created: function () {
    this.showBucketed = this.watchId !== null;
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
      this.ignoreToolFilter = hash.alltools === "1";
      if (hash.advanced === "1") {
        this.advancedQuery = true;
        this.advancedQueryStr = JSON.stringify(
          JSON.parse(hash.query || ""),
          null,
          2,
        );
      } else {
        this.showBucketed = hash.bucketed === "1";
        for (const filter of Object.keys(validFilters)) {
          if (Object.prototype.hasOwnProperty.call(hash, filter)) {
            this.filters[filter] = hash[filter];
            if (filter == "bucket") {
              this.showBucketed = true;
              this.canUnshowBucketed = false;
            }
          }
        }
      }
    }
    this.fetch();
  },
  methods: {
    addFilter: function (key, value) {
      this.filters[key] = value;
      if (key == "bucket") {
        this.showBucketed = true;
        this.canUnshowBucketed = false;
      }
      this.fetch();
    },
    buildCommonParams() {
      return {
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
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
        created__lte: this.queryTime,
      });
      return result;
    },
    buildQueryParams() {
      const result = this.buildCommonParams();
      result.vue = "1";
      result.include_raw = "0";
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
      this.cachedIgnoreToolFilter = this.ignoreToolFilter;
      this.cachedSearchStr = this.searchStr.trim();
      this.cachedShowBucketed = this.showBucketed;
    },
    buildSimpleQuery: function () {
      let query = Object.assign({ op: "AND" }, this.filters);
      const searchStr = this.searchStr.trim();
      if (searchStr !== "") {
        query["_search"] = {
          op: "OR",
          shortSignature__contains: searchStr,
          rawStderr__contains: searchStr,
          rawCrashData__contains: searchStr,
          args__contains: searchStr,
        };
      }
      if (!this.showBucketed) {
        query["bucket__isnull"] = true;
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
      this.showBucketed =
        this.watchId !== null || this.filters["bucket"] !== undefined;
      this.canUnshowBucketed = true;
      this.updateHash();
    },
    deleteQuery: async function () {
      // Create a container div for the form
      const container = document.createElement("div");

      // - show confirmation modal with affected tool breakdown
      const formCtor = createVNode(DeleteConfirmation, {
        toolCrashes: this.toolCrashes,
      });

      formCtor.appContext = getCurrentInstance()?.appContext;

      // Mount the component to get the actual DOM element
      render(formCtor, container);

      const value = await swal({
        title: "Delete these crashes?",
        content: container,
        buttons: true,
      });
      if (value) {
        // - if confirmed, submit delete and continue until done
        this.loading = true;
        let offset = 0;
        this.deleteTotal = "?";
        this.deletedEntries = 0;
        while (offset !== null) {
          try {
            const data = await api.deleteCrashes(this.buildDeleteParams());
            offset = data.nextOffset;
            if (this.deletedEntries === 0) this.deleteTotal = data.total;
            this.deletedEntries += data.deleted;
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
              break;
            } else {
              // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
              // eslint-disable-next-line no-console
              console.debug(errorParser(err));
              this.$router.go(0);
              return;
            }
          }
        }
        this.deletedEntries = null;
        this.fetch();
      }
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.updateModifiedCache();
        this.crashes = null;
        this.advancedQueryError = "";

        try {
          const data = await api.listCrashes(this.buildQueryParams());
          this.crashes = data.results;
          this.queryTime = data.query_time;
          this.toolCrashes = data.tools;
          this.currentEntries = this.crashes.length;
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
        if (key == "bucket") {
          this.canUnshowBucketed = true;
        }
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
      this.showBucketed =
        this.watchId !== null || this.filters["bucket"] !== undefined;
      this.canUnshowBucketed = true;
      this.fetch();
    },
    updateHash: function () {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
      this.updateHashSort(hash);
      if (this.ignoreToolFilter) hash.alltools = "1";
      if (this.filters["bucket"] !== undefined)
        hash.bucket = this.filters["bucket"];
      if (this.advancedQuery) {
        hash.advanced = "1";
        hash.query = encodeURIComponent(this.advancedQueryStr);
      } else {
        if (this.searchStr.trim() !== "")
          hash.search = encodeURIComponent(this.searchStr.trim());
        if (this.showBucketed) hash.bucketed = "1";
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
});
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
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}
</style>
