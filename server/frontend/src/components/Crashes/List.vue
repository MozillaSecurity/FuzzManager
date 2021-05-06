<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="glyphicon glyphicon-list-alt"></i> Crashes
    </div>
    <div class="panel-body">
      <span v-if="advancedQuery">
        <label for="id_query">Search Query</label><br />
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
          <i
            v-on:click="removeFilter(key)"
            class="glyphicon glyphicon-remove"
          ></i
          ><br />
        </span>
        <a
          title="Show the full query for the current search/filters"
          v-on:click="convertFiltersToAdvancedQuery"
          >Advanced query</a
        ><br />
      </span>
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
      <p v-else>Displaying {{ currentEntries }}/{{ totalEntries }} entries.</p>

      <div class="pagination">
        <span class="step-links">
          <a
            v-on:click="prevPage"
            v-show="currentPage > 1"
            class="glyphicon glyphicon-chevron-left"
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
            class="glyphicon glyphicon-chevron-right dimgray"
            data-original-title="Next"
          ></a>
        </span>
      </div>
    </div>
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th
            v-on:click="sortBy('id')"
            :class="{ active: sortKey === 'id' }"
            width="25px"
          >
            ID
          </th>
          <th
            v-on:click="sortBy('created')"
            :class="{ active: sortKey === 'created' }"
            width="50px"
          >
            Date Added
          </th>
          <th
            v-on:click="sortBy('bucket')"
            :class="{ active: sortKey === 'bucket' }"
            width="25px"
          >
            Bucket
          </th>
          <th
            v-on:click="sortBy('shortSignature')"
            :class="{ active: sortKey === 'shortSignature' }"
            width="100px"
          >
            Short Signature
          </th>
          <th
            v-on:click="sortBy('crashAddress')"
            :class="{ active: sortKey === 'crashAddress' }"
            width="40px"
          >
            Crash Address
          </th>
          <th
            v-on:click="sortBy('testcase__quality')"
            :class="{ active: sortKey === 'testcase__quality' }"
            width="50px"
          >
            Test Status
          </th>
          <th
            v-on:click="sortBy('product__name')"
            :class="{ active: sortKey === 'product__name' }"
            width="50px"
          >
            Product
          </th>
          <th
            v-on:click="sortBy('product__version')"
            :class="{ active: sortKey === 'product__version' }"
            width="50px"
          >
            Version
          </th>
          <th
            v-on:click="sortBy('platform__name')"
            :class="{ active: sortKey === 'platform__name' }"
            width="25px"
          >
            Platform
          </th>
          <th
            v-on:click="sortBy('os__name')"
            :class="{ active: sortKey === 'os__name' }"
            width="25px"
          >
            OS
          </th>
          <th
            v-on:click="sortBy('tool__name')"
            :class="{ active: sortKey === 'tool__name' }"
            width="40px"
          >
            Tool
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="crash in crashes" :key="crash.id">
          <td>
            <a :href="crash.view_url">{{ crash.id }}</a>
          </td>
          <td>{{ crash.created | formatDate }}</td>
          <td v-if="crash.bucket">
            <a :href="crash.sig_view_url">{{ crash.bucket }} </a>
          </td>
          <td v-else>
            <span
              v-if="!crash.triagedOnce"
              class="glyphicon glyphicon-hourglass"
              data-toggle="tooltip"
              data-placement="top"
              title="This item hasn't been triaged yet by the server."
            ></span>
            <a
              :href="crash.sig_new_url"
              data-toggle="tooltip"
              data-placement="top"
              title="Add"
              class="glyphicon glyphicon-oil dimgray"
            ></a>
            <a
              :href="crash.find_sigs_url"
              data-toggle="tooltip"
              data-placement="top"
              title="Search"
              class="glyphicon glyphicon-search dimgray"
            ></a>
          </td>
          <td>{{ crash.shortSignature }}</td>
          <td>{{ crash.crashAddress }}</td>
          <td v-if="crash.testcase">
            <a
              title="Add to search"
              class="add-filter"
              v-on:click="
                addFilter('testcase__quality', crash.testcase_quality)
              "
              >Q{{ crash.testcase_quality }}</a
            >
            {{ crash.testcase_size }}
            <span v-if="crash.testcase_isbinary">(binary)</span>
          </td>
          <td v-else>No test</td>
          <td>
            <a
              title="Add to search"
              class="add-filter"
              v-on:click="addFilter('product__name', crash.product)"
              >{{ crash.product }}</a
            >
          </td>
          <td>
            <a
              title="Add to search"
              class="add-filter"
              v-on:click="addFilter('product__version', crash.product_version)"
              >{{ crash.product_version }}</a
            >
          </td>
          <td>
            <a
              title="Add to search"
              class="add-filter"
              v-on:click="addFilter('platform__name', crash.platform)"
              >{{ crash.platform }}</a
            >
          </td>
          <td>
            <a
              title="Add to search"
              class="add-filter"
              v-on:click="addFilter('os__name', crash.os)"
            >
              <img
                v-if="crash.os === 'linux'"
                width="16px"
                height="16px"
                alt="Linux"
                :src="staticLogo('linux')"
              />
              <img
                v-else-if="crash.os === 'macosx'"
                width="16px"
                height="16px"
                alt="MacOS"
                :src="staticLogo('macosx')"
              />
              <img
                v-else-if="crash.os === 'windows'"
                width="16px"
                height="16px"
                alt="Windows"
                :src="staticLogo('windows')"
              />
              <img
                v-else-if="crash.os === 'android'"
                width="16px"
                height="16px"
                alt="Android"
                :src="staticLogo('android')"
              />
              <span v-else>{{ crash.os }}</span>
            </a>
          </td>
          <td>
            <a
              title="Add to search"
              class="add-filter"
              v-on:click="addFilter('tool__name', crash.tool)"
              >{{ crash.tool }}</a
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import _debounce from "lodash/debounce";
import _throttle from "lodash/throttle";
import sweetAlert from "sweetalert";
import { E_SERVER_ERROR, formatClientTimestamp } from "../../helpers";

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
  tool__name: "Tool",
  tool__name__contains: "Tool (sub-string match)",
};
const defaultReverse = true;
const defaultSortKey = "id";

export default {
  props: {
    restricted: {
      type: Boolean,
      required: true,
    },
    partialCrashesUrl: {
      type: String,
      required: true,
    },
  },
  data: () => ({
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
    reverse: defaultReverse,
    searchStr: "",
    showBucketed: false,
    sortKey: defaultSortKey,
    totalEntries: "?",
    totalPages: 1,
    validFilters: validFilters,
  }),
  watch: {
    advancedQueryStr: function () {
      this.debouncedFetch();
    },
    ignoreToolFilter: function () {
      this.fetch();
    },
    searchStr: function () {
      this.debouncedFetch();
    },
    showBucketed: function () {
      this.fetch();
    },
  },
  computed: {
    crashesUrl() {
      return `${this.partialCrashesUrl}?vue=1&include_raw=0&limit=${pageSize}`;
    },
  },
  created: function () {
    this.debouncedFetch = _debounce(this.fetch, 1000);
    if (location.hash.startsWith("#")) {
      const hash = location.hash
        .substring(1)
        .split(",")
        .map((v) => v.split("="))
        .reduce(
          (pre, [key, value]) => ({ ...pre, [key]: decodeURIComponent(value) }),
          {}
        );
      if (Object.prototype.hasOwnProperty.call(hash, "page")) {
        try {
          this.currentPage = Number.parseInt(hash.page, 10);
        } catch (e) {
          // eslint-disable-next-line no-console
          console.debug(`parsing '#page=\\d+': ${e}`);
        }
      }
      if (Object.prototype.hasOwnProperty.call(hash, "sort")) {
        let hashSortKey = hash.sort;
        let hashReverse = false;
        if (hashSortKey.startsWith("-")) {
          hashSortKey = hashSortKey.substring(1);
          hashReverse = true;
        }
        if (validSortKeys.includes(hashSortKey)) {
          this.sortKey = hashSortKey;
          this.reverse = hashReverse;
        } else {
          // eslint-disable-next-line no-console
          console.debug(
            `parsing '#sort=\\s+': unrecognized key '${hashSortKey}'`
          );
        }
      }
      this.ignoreToolFilter = hash.alltools === "1";
      if (hash.advanced === "1") {
        this.advancedQuery = true;
        // setting advancedQueryStr will trigger fetch
        this.advancedQueryStr = JSON.stringify(
          JSON.parse(hash.query || ""),
          null,
          2
        );
        return;
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
  filters: {
    formatDate: formatClientTimestamp,
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
    apiurl: function () {
      let params = {
        offset: `${(this.currentPage - 1) * pageSize}`,
        ordering: `${this.reverse ? "-" : ""}${this.sortKey}`,
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
      };
      if (this.advancedQuery) {
        params.query = encodeURIComponent(this.advancedQueryStr);
      } else {
        params.query = encodeURIComponent(
          JSON.stringify(this.buildSimpleQuery())
        );
      }
      return `${this.crashesUrl}&${Object.entries(params)
        .map((kv) => kv.join("="))
        .join("&")}`;
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
      this.showBucketed = false;
      this.canUnshowBucketed = true;
      this.updateHash();
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.advancedQueryError = "";
        try {
          const response = await fetch(this.apiurl(), {
            method: "GET",
            credentials: "same-origin",
          });
          if (response.ok) {
            const data = await response.json();
            this.crashes = data["results"];
            this.currentEntries = this.crashes.length;
            this.totalEntries = data["count"];
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
          } else {
            if (this.advancedQuery) {
              response.json().then((val) => {
                this.advancedQueryError = val.detail;
              });
            } else {
              // TODO: this should set advancedQueryError when in advanced mode
              // eslint-disable-next-line no-console
              response.text().then(console.debug);
              sweetAlert("Oops", E_SERVER_ERROR, "error");
            }
            this.loading = false;
          }
        } catch (e) {
          // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
          // eslint-disable-next-line no-console
          console.debug(e);
          location.reload();
          return;
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
      this.showBucketed = false;
      this.canUnshowBucketed = true;
      this.fetch();
    },
    sortBy: function (sortKey) {
      const keyChange = this.sortKey !== sortKey;
      this.reverse = !keyChange ? !this.reverse : false;
      this.sortKey = sortKey;
      this.fetch();
    },
    staticLogo(name) {
      return window.location.origin + "/static/img/os/" + name + ".png";
    },
    updateHash: function () {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
      if (this.sortKey !== defaultSortKey || this.reverse !== defaultReverse) {
        hash.sort = (this.reverse ? "-" : "") + this.sortKey;
      }
      if (this.ignoreToolFilter) hash.alltools = "1";
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
        location.hash =
          "#" +
          Object.entries(hash)
            .map((kv) => kv.join("="))
            .join();
      } else {
        location.hash = "";
      }
    },
  },
};
</script>

<style scoped>
.add-filter {
  cursor: crosshair;
}
.dimgray {
  color: dimgray;
}
.monospace {
  font-family: monospace;
}
</style>
