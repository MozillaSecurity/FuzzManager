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
        <span id="help-hint-query">
          <i class="glyphicon glyphicon-question-sign"></i>
        </span>
        <b-popover target="help-hint-query" triggers="hover" placement="top">
          <div class="pop-header">Available query parameters</div>
          <div class="pop-body">
            <h4>
              Available parameters
              <button
                class="btn btn-default btn-xs pull-right ml-5"
                v-on:click="showParams = !showParams"
              >
                <i class="glyphicon glyphicon-minus" v-if="showParams"></i>
                <i class="glyphicon glyphicon-plus" v-else></i>
              </button>
            </h4>
            <div class="pop-list mt-1" v-if="showParams">
              <p><code>id</code>: Integer (ID)</p>
              <p><code>signature</code>: String</p>
              <p><code>optimizedSignature</code>: String</p>
              <p><code>shortDescription</code>: String</p>
              <p><code>frequent</code>: Boolean</p>
              <p><code>permanent</code>: Boolean</p>
              <p><code>bug</code>: Integer (ID)</p>
              <p><code>bug__externalId</code>: String</p>
              <p><code>bug__closed</code>: Date</p>
              <p><code>bug__externalType</code>: Integer (ID)</p>
              <p><code>bug__externalType__classname</code>: String</p>
              <p><code>bug__externalType__hostname</code>: String</p>
            </div>
            <hr />
            <h4>
              Usable operations
              <button
                class="btn btn-default btn-xs pull-right ml-5"
                v-on:click="showOps = !showOps"
              >
                <i class="glyphicon glyphicon-minus" v-if="showOps"></i>
                <i class="glyphicon glyphicon-plus" v-else></i>
              </button>
            </h4>
            <div class="pop-list mt-1" v-if="showOps">
              <p><code>__contains</code>: String</p>
              <p><code>__in</code>: Iterable</p>
              <p><code>__gt</code>: Integer</p>
              <p><code>__gte</code>: Integer</p>
              <p><code>__lt</code>: Integer</p>
              <p><code>__lte</code>: Integer</p>
              <p><code>__startswith</code>: String</p>
              <p><code>__endswith</code>: String</p>
              <p><code>__isnull</code>: Boolean</p>
              <a
                class="pull-right"
                target="_blank"
                href="https://docs.djangoproject.com/fr/3.2/ref/models/querysets/#field-lookups"
              >
                More operations
              </a>
            </div>
          </div>
        </b-popover>
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
            v-on:click.exact="sortBy('id')"
            v-on:click.ctrl.exact="addSort('id')"
            :class="{
              active: sortKeys.includes('id') || sortKeys.includes('-id'),
            }"
            width="20px"
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
            width="150px"
          >
            Short Description
          </th>
          <th
            v-on:click.exact="sortBy('size')"
            v-on:click.ctrl.exact="addSort('size')"
            :class="{
              active: sortKeys.includes('size') || sortKeys.includes('-size'),
            }"
            width="20px"
          >
            Bucket Size
          </th>
          <th
            v-on:click.exact="sortBy('quality')"
            v-on:click.ctrl.exact="addSort('quality')"
            :class="{
              active:
                sortKeys.includes('quality') || sortKeys.includes('-quality'),
            }"
            width="25px"
          >
            Best Test Quality
          </th>
          <th
            v-on:click.exact="sortBy('bug__externalId')"
            v-on:click.ctrl.exact="addSort('bug__externalId')"
            :class="{
              active:
                sortKeys.includes('bug__externalId') ||
                sortKeys.includes('-bug__externalId'),
            }"
            width="50px"
          >
            External Bug
          </th>
          <th
            v-on:click.exact="sortBy('optimizedSignature')"
            v-on:click.ctrl.exact="addSort('optimizedSignature')"
            :class="{
              active:
                sortKeys.includes('optimizedSignature') ||
                sortKeys.includes('-optimizedSignature'),
            }"
            width="30px"
          >
            Pending Optimization
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="6">
            <ClipLoader class="m-strong" :color="'black'" :size="'50px'" />
          </td>
        </tr>
        <Row
          v-for="signature in signatures"
          :key="signature.id"
          :signature="signature"
          v-else
        />
      </tbody>
    </table>
  </div>
</template>

<script>
import _debounce from "lodash/debounce";
import _throttle from "lodash/throttle";
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
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
const defaultSortKey = "-id";
const pageSize = 100;

export default {
  components: {
    Row,
    ClipLoader,
  },
  props: {
    watchUrl: {
      type: String,
      required: true,
    },
  },
  data: () => ({
    signatures: [],
    sortKeys: [defaultSortKey],
    queryStr: JSON.stringify({ op: "AND", bug__isnull: true }, null, 2),
    queryError: "",
    ignoreToolFilter: false,
    searchStr: "",
    currentPage: 1,
    currentEntries: "?",
    totalEntries: "?",
    totalPages: 1,
    loading: false,
    showParams: true,
    showOps: false,
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
      this.fetch();
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
      this.fetch();
    },
    buildParams() {
      return {
        vue: "1",
        limit: pageSize,
        offset: `${(this.currentPage - 1) * pageSize}`,
        ordering: this.sortKeys.join(),
        ignore_toolfilter: this.ignoreToolFilter ? "1" : "0",
        query: this.queryStr,
      };
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        this.signatures = null;
        this.currentEntries = "?";
        this.totalEntries = "?";
        this.currentPage = 1;
        this.totalPages = 1;
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
    updateHash() {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
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
};
</script>

<style scoped>
.m-strong {
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
}
.ml-5 {
  margin-left: 5rem;
}
.mt-1 {
  margin-top: 1rem;
}
.pop-header {
  padding: 1rem;
  margin-bottom: 0;
  background-color: #f7f7f7;
  border-bottom: 1px solid #ebebeb;
  font-size: 1.5rem;
  font-weight: bold;
}
.pop-body {
  padding: 1rem;
  color: #212529;
}
.pop-body a {
  margin-bottom: 1rem;
}
.pop-list p {
  margin-bottom: 0.25rem;
}
</style>
