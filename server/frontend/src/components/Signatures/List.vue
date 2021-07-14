<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="glyphicon glyphicon-tag"></i> Signatures
    </div>
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
      </div>
      <br />
      <p v-if="showAll">
        Displaying {{ currentEntries }}/{{ totalEntries }} of all signature
        entries in the database.
      </p>
      <p v-else>
        Displaying {{ currentEntries }}/{{ totalEntries }} unreported signature
        entries from the database.
      </p>

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
            width="20px"
          >
            ID
          </th>
          <th
            v-on:click="sortBy('shortDescription')"
            :class="{ active: sortKey === 'shortDescription' }"
            width="150px"
          >
            Short Description
          </th>
          <th
            v-on:click="sortBy('size')"
            :class="{ active: sortKey === 'size' }"
            width="20px"
          >
            Bucket Size
          </th>
          <th
            v-on:click="sortBy('quality')"
            :class="{ active: sortKey === 'quality' }"
            width="25px"
          >
            Best Test Quality
          </th>
          <th
            v-on:click="sortBy('bug__externalId')"
            :class="{ active: sortKey === 'bug__externalId' }"
            width="50px"
          >
            External Bug
          </th>
          <th
            v-on:click="sortBy('optimizedSignature')"
            :class="{ active: sortKey === 'optimizedSignature' }"
            width="30px"
          >
            Pending Optimization
          </th>
        </tr>
      </thead>
      <tbody>
        <Row
          v-for="signature in signatures"
          :key="signature.id"
          :signature="signature"
        />
      </tbody>
    </table>
  </div>
</template>

<script>
import _debounce from "lodash/debounce";
import _throttle from "lodash/throttle";
import { errorParser, parseHash } from "../../helpers";
import * as api from "../../api";
import Row from "./Row.vue";

const validSortKeys = [
  "id",
  "shortDescription",
  "size",
  "quality",
  "optimizedSignature",
  "bug__externalId",
];
const defaultReverse = true;
const defaultSortKey = "id";
const pageSize = 100;

export default {
  components: {
    Row,
  },
  props: {
    watchUrl: {
      type: String,
      required: true,
    },
  },
  data: () => ({
    signatures: [],
    reverse: defaultReverse,
    sortKey: defaultSortKey,
    queryStr: JSON.stringify({ op: "AND", bug__isnull: true }, null, 2),
    queryError: "",
    ignoreToolFilter: false,
    searchStr: "",
    currentPage: 1,
    currentEntries: "?",
    totalEntries: "?",
    totalPages: 1,
  }),
  watch: {
    queryStr() {
      this.debouncedFetch();
    },
    ignoreToolFilter() {
      this.fetch();
    },
  },
  created() {
    if (this.$route.query.all)
      this.queryStr = JSON.stringify({ op: "AND" }, null, 2);
    if (this.$route.query.ids)
      this.queryStr = JSON.stringify(
        { op: "AND", id__in: this.$route.query.ids.split(",") },
        null,
        2
      );
    this.debouncedFetch = _debounce(this.fetch, 1000);
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
      if (Object.prototype.hasOwnProperty.call(hash, "query")) {
        this.queryStr = JSON.stringify(JSON.parse(hash.query || ""), null, 2);
      }
    }
    this.fetch();
  },
  computed: {
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
    sortBy(sortKey) {
      const keyChange = this.sortKey !== sortKey;
      this.reverse = !keyChange ? !this.reverse : false;
      this.sortKey = sortKey;
      this.fetch();
    },
    buildParams() {
      return {
        vue: "1",
        limit: pageSize,
        offset: `${(this.currentPage - 1) * pageSize}`,
        ordering: `${this.reverse ? "-" : ""}${this.sortKey}`,
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
        query: this.queryStr,
      };
    },
    fetch: _throttle(
      async function () {
        this.queryError = "";
        try {
          const data = await api.listBuckets(this.buildParams());
          this.signatures = data.results;
          this.currentEntries = this.signatures.length;
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
            this.queryError = err.response.data.detail;
          } else {
            // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
            // eslint-disable-next-line no-console
            console.debug(errorParser(err));
            this.$router.go(0);
            return;
          }
        }
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
    updateHash() {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
      if (this.sortKey !== defaultSortKey || this.reverse !== defaultReverse) {
        hash.sort = (this.reverse ? "-" : "") + this.sortKey;
      }
      if (this.queryStr) hash.query = encodeURIComponent(this.queryStr);
      if (this.ignoreToolFilter) hash.alltools = "1";
      if (Object.entries(hash).length) {
        const routeHash =
          "#" +
          Object.entries(hash)
            .map((kv) => kv.join("="))
            .join();
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

<style scoped></style>
