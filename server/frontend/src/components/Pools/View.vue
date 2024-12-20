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
      <table class="table table-condensed table-hover table-bordered table-db">
        <thead>
          <tr>
            <th
              :class="{
                active:
                  sortKeys.includes('task_id') || sortKeys.includes('-task_id'),
              }"
              width="50px"
              @click.exact="sortBy('task_id')"
              @click.ctrl.exact="addSort('task_id')"
            >
              Task
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('run_id') || sortKeys.includes('-run_id'),
              }"
              width="15px"
              @click.exact="sortBy('run_id')"
              @click.ctrl.exact="addSort('run_id')"
            >
              Run
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('state') || sortKeys.includes('-state'),
              }"
              width="25px"
              @click.exact="sortBy('state')"
              @click.ctrl.exact="addSort('state')"
            >
              State
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('created') || sortKeys.includes('-created'),
              }"
              width="60px"
              @click.exact="sortBy('created')"
              @click.ctrl.exact="addSort('created')"
            >
              Created
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('started') || sortKeys.includes('-started'),
              }"
              width="60px"
              @click.exact="sortBy('started')"
              @click.ctrl.exact="addSort('started')"
            >
              Started
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('resolved') ||
                  sortKeys.includes('-resolved'),
              }"
              width="60px"
              @click.exact="sortBy('resolved')"
              @click.ctrl.exact="addSort('resolved')"
            >
              Resolved
            </th>
            <th
              :class="{
                active:
                  sortKeys.includes('expires') || sortKeys.includes('-expires'),
              }"
              width="60px"
              @click.exact="sortBy('expires')"
              @click.ctrl.exact="addSort('expires')"
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
              {{ formatDate(task.created) }}<br />{{
                formatDateAgo(task.created)
              }}
            </td>
            <td v-if="task.started !== null">
              {{ formatDate(task.started) }}<br />{{
                formatDateRelative(task.created, task.started, "later")
              }}
            </td>
            <td v-else>N/A</td>
            <td v-if="task.resolved !== null">
              {{ formatDate(task.resolved) }}<br />{{
                formatDateRelative(
                  task.started !== null ? task.started : task.created,
                  task.resolved,
                  "later",
                )
              }}
            </td>
            <td v-else>N/A</td>
            <td>
              {{ formatDate(task.expires) }}<br />{{
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
import {
  defineComponent,
  getCurrentInstance,
  onMounted,
  ref,
  watch,
} from "vue";
import * as api from "../../api";
import {
  E_SERVER_ERROR,
  formatClientTimestamp,
  formatDateRelative,
  multiSort,
  parseHash,
} from "../../helpers";

const pageSize = 100;

export default defineComponent({
  mixins: [multiSort],
  props: {
    pool: {
      type: Object,
      default: null,
    },
  },
  setup(props) {
    // State
    const currentEntries = ref("?");
    const currentPage = ref(1);
    const loading = ref(true);
    const tasks = ref(null);
    const totalEntries = ref("?");
    const totalPages = ref(1);

    // Sort keys
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
    const sortKeys = ref([...defaultSortKeys]);

    // Methods
    const buildParams = () => {
      return {
        vue: "1",
        limit: pageSize,
        offset: `${(currentPage.value - 1) * pageSize}`,
        ordering: sortKeys.value.join(),
        query: JSON.stringify({
          op: "OR",
          pool: props.pool.id,
        }),
      };
    };

    const fetch = _throttle(
      async () => {
        loading.value = true;
        try {
          const data = await api.listTasks(buildParams());
          tasks.value = data.results;
          currentEntries.value = tasks.value.length;
          totalEntries.value = data.count;
          totalPages.value = Math.max(
            Math.ceil(totalEntries.value / pageSize),
            1,
          );
          if (currentPage.value > totalPages.value) {
            currentPage.value = totalPages.value;
            fetch();
            return;
          }
          updateHash();
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            console.debug(err.response.data);
            swal("Oops", E_SERVER_ERROR, "error");
            loading.value = false;
          }
        }
        loading.value = false;
      },
      500,
      { trailing: true },
    );

    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--;
        fetch();
      }
    };

    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++;
        fetch();
      }
    };

    const instance = getCurrentInstance();
    const updateHash = () => {
      let hash = {};
      if (currentPage.value !== 1) {
        hash.page = currentPage.value;
      }
      // Note: updateHashSort comes from mixin
      instance.proxy.updateHashSort(hash);
      if (Object.entries(hash).length) {
        location.hash =
          "#" +
          Object.entries(hash)
            .map((kv) => kv.join("="))
            .join("&");
      } else {
        location.hash = "";
      }
    };

    onMounted(() => {
      if (location.hash.startsWith("#")) {
        const hash = parseHash(location.hash);
        if (Object.prototype.hasOwnProperty.call(hash, "page")) {
          try {
            currentPage.value = Number.parseInt(hash.page, 10);
          } catch (e) {
            console.debug(`parsing '#page=\\d+': ${e}`);
          }
        }
      }
      fetch();
    });

    watch(sortKeys, () => {
      fetch();
    });

    return {
      currentEntries,
      currentPage,
      loading,
      sortKeys,
      tasks,
      totalEntries,
      totalPages,
      defaultSortKeys,
      validSortKeys,
      fetch,
      prevPage,
      nextPage,
      updateHash,
    };
  },
  methods: {
    formatDate: formatClientTimestamp,
    formatDateAgo: formatDateRelative,
    formatDateRelative,
  },
});
</script>

<style scoped>
.dimgray {
  color: dimgray;
}
</style>
