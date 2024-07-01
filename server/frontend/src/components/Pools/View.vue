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
              v-on:click.exact="sortBy('task_id')"
              v-on:click.ctrl.exact="addSort('task_id')"
              :class="{
                active:
                  sortKeys.includes('task_id') || sortKeys.includes('-task_id'),
              }"
              width="50px"
            >
              Task
            </th>
            <th
              v-on:click.exact="sortBy('run_id')"
              v-on:click.ctrl.exact="addSort('run_id')"
              :class="{
                active:
                  sortKeys.includes('run_id') || sortKeys.includes('-run_id'),
              }"
              width="15px"
            >
              Run
            </th>
            <th
              v-on:click.exact="sortBy('state')"
              v-on:click.ctrl.exact="addSort('state')"
              :class="{
                active:
                  sortKeys.includes('state') || sortKeys.includes('-state'),
              }"
              width="25px"
            >
              State
            </th>
            <th
              v-on:click.exact="sortBy('created')"
              v-on:click.ctrl.exact="addSort('created')"
              :class="{
                active:
                  sortKeys.includes('created') || sortKeys.includes('-created'),
              }"
              width="60px"
            >
              Created
            </th>
            <th
              v-on:click.exact="sortBy('started')"
              v-on:click.ctrl.exact="addSort('started')"
              :class="{
                active:
                  sortKeys.includes('started') || sortKeys.includes('-started'),
              }"
              width="60px"
            >
              Started
            </th>
            <th
              v-on:click.exact="sortBy('resolved')"
              v-on:click.ctrl.exact="addSort('resolved')"
              :class="{
                active:
                  sortKeys.includes('resolved') ||
                  sortKeys.includes('-resolved'),
              }"
              width="60px"
            >
              Resolved
            </th>
            <th
              v-on:click.exact="sortBy('expires')"
              v-on:click.ctrl.exact="addSort('expires')"
              :class="{
                active:
                  sortKeys.includes('expires') || sortKeys.includes('-expires'),
              }"
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
              <a
                v-if="task.started !== null"
                :href="
                  `https://console.cloud.google.com/logs/query;query=jsonPayload.host%3D%22task-${task.task_id}-run-${task.run_id}%22;timeRange=${task.started}%2F` +
                  (task.resolved !== null ? task.resolved : '') +
                  '?project=fuzzmanager-cluster&supportedpurview=project'
                "
              >
                (logs)</a
              >
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
                  "later",
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
  multiSort,
} from "../../helpers";

const pageSize = 100;

export default {
  mixins: [multiSort],
  data: function () {
    const defaultSortKeys = ["-created", "-state", "task_id"];
    const validSortKeys = [
      "created",
      "expires",
      "resolved",
      "run_id",
      "started",
      "state",
      "task_id",
    ];
    return {
      currentEntries: "?",
      currentPage: 1,
      defaultSortKeys: defaultSortKeys,
      loading: true,
      sortKeys: [...defaultSortKeys],
      tasks: null,
      totalEntries: "?",
      totalPages: 1,
      validSortKeys: validSortKeys,
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
        ordering: this.sortKeys.join(),
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
            // eslint-disable-next-line no-console
            console.debug(err.response.data);
            swal("Oops", E_SERVER_ERROR, "error");
            this.loading = false;
          }
        }
        this.loading = false;
      },
      500,
      { trailing: true },
    ),
    formatDateRelative: formatDateRelative,
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
      this.updateHashSort(hash);
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
</style>
