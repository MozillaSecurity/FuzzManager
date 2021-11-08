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
        <label for="id_bucketed">Include Bucketed</label>:
        <input
          id="id_bucketed"
          type="checkbox"
          name="bucketed"
          :disabled="!canUnshowBucketed"
          v-model="showBucketed"
        /><br />
      </span>
      <template v-if="!restricted">
        <label for="id_no_toolfilter">Ignore Tool Filter</label>:
        <input
          id="id_no_toolfilter"
          type="checkbox"
          name="alltools"
          v-model="ignoreToolFilter"
        /><br />
      </template>
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
    </div>
    <div class="panel-body">
      <p
        v-if="
          advancedQuery ||
          searchStr.trim() !== '' ||
          Object.keys(filters).length
        "
      >
        Displaying {{ currentEntries }}/{{ totalEntries }} entries matching
        query.
      </p>
      <p v-else-if="!showBucketed">
        Displaying {{ currentEntries }}/{{ totalEntries }} unbucketed entries.
      </p>
      <p v-else-if="watchId !== null && crashes">
        Displaying {{ currentEntries }} new entries in bucket
        {{ crashes[0].bucket }}.
      </p>
      <p v-else>Displaying {{ currentEntries }}/{{ totalEntries }} entries.</p>

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
              v-on:click.exact="sortBy('id')"
              v-on:click.ctrl.exact="addSort('id')"
              :class="{
                active: sortKeys.includes('id') || sortKeys.includes('-id'),
              }"
            >
              ID
            </th>
            <th
              v-on:click.exact="sortBy('created')"
              v-on:click.ctrl.exact="addSort('created')"
              :class="{
                active:
                  sortKeys.includes('created') || sortKeys.includes('-created'),
              }"
            >
              Date Added
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
              v-on:click.exact="sortBy('shortSignature')"
              v-on:click.ctrl.exact="addSort('shortSignature')"
              :class="{
                active:
                  sortKeys.includes('shortSignature') ||
                  sortKeys.includes('-shortSignature'),
              }"
            >
              Short Signature
            </th>
            <th
              v-on:click.exact="sortBy('crashAddress')"
              v-on:click.ctrl.exact="addSort('crashAddress')"
              :class="{
                active:
                  sortKeys.includes('crashAddress') ||
                  sortKeys.includes('-crashAddress'),
              }"
            >
              Crash Address
            </th>
            <th
              v-on:click.exact="sortBy('testcase__size')"
              v-on:click.ctrl.exact="addSort('testcase__size')"
              :class="{
                active:
                  sortKeys.includes('testcase__size') ||
                  sortKeys.includes('-testcase__size'),
              }"
            >
              Test Size
            </th>
            <th
              v-on:click.exact="sortBy('testcase__quality')"
              v-on:click.ctrl.exact="addSort('testcase__quality')"
              :class="{
                active:
                  sortKeys.includes('testcase__quality') ||
                  sortKeys.includes('-testcase__quality'),
              }"
            >
              Test Info
            </th>
            <th
              v-on:click.exact="sortBy('product__name')"
              v-on:click.ctrl.exact="addSort('product__name')"
              :class="{
                active:
                  sortKeys.includes('product__name') ||
                  sortKeys.includes('-product__name'),
              }"
            >
              Product
            </th>
            <th
              v-on:click.exact="sortBy('product__version')"
              v-on:click.ctrl.exact="addSort('product__version')"
              :class="{
                active:
                  sortKeys.includes('product__version') ||
                  sortKeys.includes('-product__version'),
              }"
            >
              Version
            </th>
            <th
              v-on:click.exact="sortBy('platform__name')"
              v-on:click.ctrl.exact="addSort('platform__name')"
              :class="{
                active:
                  sortKeys.includes('platform__name') ||
                  sortKeys.includes('-platform__name'),
              }"
            >
              Platform
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
            <th
              v-on:click.exact="sortBy('tool__name')"
              v-on:click.ctrl.exact="addSort('tool__name')"
              :class="{
                active:
                  sortKeys.includes('tool__name') ||
                  sortKeys.includes('-tool__name'),
              }"
            >
              Tool
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="11">
              <ClipLoader class="m-strong" :color="'black'" :size="'50px'" />
            </td>
          </tr>
          <Row
            v-for="crash in crashes"
            :key="crash.id"
            :crash="crash"
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
import { errorParser, E_SERVER_ERROR, parseHash } from "../../helpers";
import * as api from "../../api";
import Row from "./Row.vue";
import HelpJSONQueryPopover from "../HelpJSONQueryPopover.vue";

const pageSize = 100;
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
const defaultSortKey = "-id";

export default {
  components: {
    Row,
    ClipLoader,
    HelpJSONQueryPopover,
  },
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
  data: () => ({
    modifiedCache: {},
    advancedQuery: false,
    advancedQueryError: "",
    advancedQueryStr: "",
    canUnshowBucketed: true,
    crashes: null,
    currentEntries: "?",
    currentPage: 1,
    filters: {},
    ignoreToolFilter: false,
    loading: true,
    searchStr: "",
    showBucketed: false,
    sortKeys: [defaultSortKey],
    totalEntries: "?",
    totalPages: 1,
    validFilters: validFilters,
  }),
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
      if (Object.prototype.hasOwnProperty.call(hash, "bucket"))
        this.filters["bucket"] = hash.bucket;
      this.ignoreToolFilter = hash.alltools === "1";
      if (hash.advanced === "1") {
        this.advancedQuery = true;
        this.advancedQueryStr = JSON.stringify(
          JSON.parse(hash.query || ""),
          null,
          2
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
  computed: {
    modified() {
      if (this.ignoreToolFilter !== this.modifiedCache.ignoreToolFilter)
        return true;
      if (this.advancedQuery) {
        const queryStr = (() => {
          try {
            return JSON.parse(this.advancedQueryStr);
          } catch (e) {} // eslint-disable-line no-empty
        })();
        return !_isEqual(queryStr, this.modifiedCache.advancedQueryStr);
      }
      return (
        this.showBucketed !== this.modifiedCache.showBucketed ||
        this.searchStr.trim() !== this.modifiedCache.searchStr
      );
    },
    queryButtonTitle() {
      if (this.loading) return "Query in progress";
      if (!this.modified) return "Results match current query";
      return "Submit query";
    },
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
    buildParams() {
      return {
        vue: "1",
        include_raw: "0",
        limit: pageSize,
        offset: `${(this.currentPage - 1) * pageSize}`,
        ordering: this.sortKeys.join(),
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
        query: this.advancedQuery
          ? this.advancedQueryStr
          : JSON.stringify(this.buildSimpleQuery()),
        watch: this.watchId === null ? false : this.watchId,
      };
    },
    updateModifiedCache() {
      try {
        // ignore query errors
        this.modifiedCache.advancedQueryStr = JSON.parse(this.advancedQueryStr);
      } catch (e) {} // eslint-disable-line no-empty
      this.modifiedCache.ignoreToolFilter = this.ignoreToolFilter;
      this.modifiedCache.searchStr = this.searchStr.trim();
      this.modifiedCache.showBucketed = this.showBucketed;
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
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.updateModifiedCache();
        this.crashes = null;
        this.advancedQueryError = "";
        try {
          const data = await api.listCrashes(this.buildParams());
          this.crashes = data.results;
          this.currentEntries = this.crashes.length;
          this.totalEntries = data.count;
          this.totalPages = Math.max(
            Math.ceil(this.totalEntries / pageSize),
            1
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
      { trailing: true }
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
          this.sortKeys.unshift(`-${sortKey}`);
        }
      }
      this.fetch();
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
        this.sortKeys = [`-${sortKey}`];
      }
      this.fetch();
    },
    updateHash: function () {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
      if (this.sortKeys.length !== 1 || this.sortKeys[0] !== defaultSortKey) {
        hash.sort = this.sortKeys.join();
      }
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
