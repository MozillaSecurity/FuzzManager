<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-bar-chart-steps"></i> Pool Status
    </div>
    <div class="panel-body">
      <table class="table">
        <tbody>
          <tr>
            <td>Pool ID:</td>
            <td>
              <a :href="pool.hook_url">{{ pool.pool_id }}</a>
            </td>
          </tr>
          <tr>
            <td>Pool Name:</td>
            <td>{{ pool.pool_name }}</td>
          </tr>
          <tr>
            <td>Platform:</td>
            <td>{{ pool.platform }}</td>
          </tr>
          <tr>
            <td>Size:</td>
            <td>{{ pool.size }}</td>
          </tr>
          <tr>
            <td>CPU:</td>
            <td>{{ pool.cpu }}</td>
          </tr>
          <tr>
            <td>Cycle Time:</td>
            <td>
              {{ formatDateRelative(new Date(pool.cycle_time * 1000), 0, "") }}
            </td>
          </tr>
          <tr>
            <td>Max. Run Time:</td>
            <td>
              {{
                formatDateRelative(new Date(pool.max_run_time * 1000), 0, "")
              }}
            </td>
          </tr>
        </tbody>
      </table>
      <hr />
      <p>Displaying {{ currentEntries }}/{{ totalEntries }} entries.</p>
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
      <table class="table table-condensed table-hover table-bordered table-db">
        <thead>
          <tr>
            <th
              v-on:click="sortBy('task_id')"
              :class="{ active: sortKey === 'task_id' }"
              width="50px"
            >
              Task
            </th>
            <th
              v-on:click="sortBy('run_id')"
              :class="{ active: sortKey === 'run_id' }"
              width="15px"
            >
              Run
            </th>
            <th
              v-on:click="sortBy('state')"
              :class="{ active: sortKey === 'state' }"
              width="25px"
            >
              State
            </th>
            <th
              v-on:click="sortBy('created')"
              :class="{ active: sortKey === 'created' }"
              width="60px"
            >
              Created
            </th>
            <th
              v-on:click="sortBy('started')"
              :class="{ active: sortKey === 'started' }"
              width="60px"
            >
              Started
            </th>
            <th
              v-on:click="sortBy('resolved')"
              :class="{ active: sortKey === 'resolved' }"
              width="60px"
            >
              Resolved
            </th>
            <th
              v-on:click="sortBy('expires')"
              :class="{ active: sortKey === 'expires' }"
              width="60px"
            >
              Expires
            </th>
            <th width="150px">Status Data</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id">
            <td>
              <a :href="task.task_url">{{ task.task_id }}</a>
            </td>
            <td>{{ task.run_id }}</td>
            <td>
              <span
                class="label"
                :class="{
                  'label-default': task.state === 'pending',
                  'label-warning': task.state === 'exception',
                  'label-primary': task.state === 'running',
                  'label-danger': task.state === 'failed',
                  'label-success': task.state === 'completed',
                }"
                >{{ task.state }}</span
              >
            </td>
            <td>
              {{ task.created | formatDate }}<br />{{
                task.created | formatDateAgo
              }}
            </td>
            <td v-if="task.started !== null">
              {{ task.started | formatDate }}<br />{{
                formatDateRelative(task.created, task.started, "later")
              }}
            </td>
            <td v-else>N/A</td>
            <td v-if="task.resolved !== null">
              {{ task.resolved | formatDate }}<br />{{
                formatDateRelative(
                  task.started !== null ? task.started : task.created,
                  task.resolved,
                  "later"
                )
              }}
            </td>
            <td v-else>N/A</td>
            <td>
              {{ task.expires | formatDate }}<br />{{
                new Date(task.expires) > new Date()
                  ? formatDateRelative(new Date(), task.expires, "from now")
                  : formatDateRelative(task.expires)
              }}
            </td>
            <td v-if="task.status_data">
              <pre>{{ task.status_data }}</pre>
            </td>
            <td v-else>N/A</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import _throttle from "lodash/throttle";
import swal from "sweetalert";
import * as api from "../../api";
import {
  formatClientTimestamp,
  formatDateRelative,
  E_SERVER_ERROR,
  parseHash,
} from "../../helpers";

const pageSize = 100;
const validSortKeys = [
  "task_id",
  "run_id",
  "state",
  "created",
  "started",
  "resolved",
  "expires",
];
const defaultReverse = true;
const defaultSortKey = "created";

export default {
  data: function () {
    return {
      currentEntries: "?",
      currentPage: 1,
      loading: true,
      reverse: defaultReverse,
      sortKey: defaultSortKey,
      tasks: null,
      totalEntries: "?",
      totalPages: 1,
    };
  },
  props: {
    pool: {
      type: Object,
      default: null,
    },
  },
  created: function () {
    if (location.hash.startsWith("#")) {
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
    }
    this.fetch();
  },
  filters: {
    formatDate: formatClientTimestamp,
    formatDateAgo: formatDateRelative,
  },
  methods: {
    buildParams() {
      return {
        vue: "1",
        limit: pageSize,
        offset: `${(this.currentPage - 1) * pageSize}`,
        ordering: `${this.reverse ? "-" : ""}${this.sortKey}`,
        query: JSON.stringify({
          op: "OR",
          pool: this.pool.id,
        }),
      };
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        try {
          const data = await api.listTasks(this.buildParams());
          this.tasks = data.results;
          this.currentEntries = this.tasks.length;
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
            // eslint-disable-next-line no-console
            console.debug(err.response.data);
            swal("Oops", E_SERVER_ERROR, "error");
            this.loading = false;
          }
        }
        this.loading = false;
      },
      500,
      { trailing: true }
    ),
    formatDateRelative: formatDateRelative,
    sortBy: function (sortKey) {
      const keyChange = this.sortKey !== sortKey;
      this.reverse = !keyChange ? !this.reverse : false;
      this.sortKey = sortKey;
      if (keyChange || this.totalPages > 1) {
        this.fetch();
      } else {
        this.updateHash();
      }
    },
    prevPage: function () {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetch();
      }
    },
    nextPage: function () {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.fetch();
      }
    },
    updateHash: function () {
      let hash = {};
      if (this.currentPage !== 1) {
        hash.page = this.currentPage;
      }
      if (this.sortKey !== defaultSortKey || this.reverse !== defaultReverse) {
        hash.sort = (this.reverse ? "-" : "") + this.sortKey;
      }
      if (Object.entries(hash).length) {
        location.hash =
          "#" +
          Object.entries(hash)
            .map((kv) => kv.join("="))
            .join("&");
      } else {
        location.hash = "";
      }
    },
  },
};
</script>

<style scoped>
.dimgray {
  color: dimgray;
}
</style>
