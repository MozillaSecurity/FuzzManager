<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-card-list"></i> Fuzzing Pools
    </div>
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th
            :class="{
              active:
                sortKeys.includes('pool_id') || sortKeys.includes('-pool_id'),
            }"
            width="25px"
            @click.exact="sortBy('pool_id')"
            @click.ctrl.exact="addSort('pool_id')"
          >
            ID
          </th>
          <th
            :class="{
              active:
                sortKeys.includes('pool_name_isort') ||
                sortKeys.includes('-pool_name_isort'),
            }"
            width="100px"
            @click.exact="sortBy('pool_name_isort')"
            @click.ctrl.exact="addSort('pool_name_isort')"
          >
            Name
          </th>
          <th
            :class="{
              active:
                sortKeys.includes('running') || sortKeys.includes('-running'),
            }"
            width="75px"
            @click.exact="sortBy('running')"
            @click.ctrl.exact="addSort('running')"
          >
            # of Tasks (Running/Requested)
          </th>
          <th
            :class="{
              active:
                sortKeys.includes('status') || sortKeys.includes('-status'),
            }"
            width="150px"
            @click.exact="sortBy('status')"
            @click.ctrl.exact="addSort('status')"
          >
            Status
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pool in orderedPools" :key="pool.id">
          <td>
            <a :href="pool.view_url">{{ pool.pool_id }}</a>
          </td>
          <td>{{ pool.pool_name }}</td>
          <td>{{ pool.running }}/{{ pool.size }}</td>
          <td>
            <span
              class="label"
              :class="{
                'label-warning': pool.status === 'partial',
                'label-success': pool.status === 'healthy',
                'label-danger': pool.status === 'idle',
                'label-default': pool.status === 'disabled',
              }"
              >{{ pool.status }}</span
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import _throttle from "lodash/throttle";
import swal from "sweetalert";
import { computed, defineComponent, ref } from "vue";
import * as api from "../../api";
import { E_SERVER_ERROR, multiSort } from "../../helpers";

export default defineComponent({
  name: "PoolsList",
  mixins: [multiSort],
  setup() {
    const defaultSortKeys = ["pool_name_isort"];
    const validSortKeys = ["pool_id", "pool_name_isort", "running", "status"];
    const loading = ref(true);
    const pools = ref(null);
    const sortKeys = ref([...defaultSortKeys]);

    const buildParams = () => {
      return {
        vue: "1",
      };
    };

    const fetch = _throttle(
      async () => {
        loading.value = true;
        try {
          const data = await api.listPools(buildParams());
          pools.value = data.map((pool) => {
            pool.pool_name_isort = pool.pool_name.toLowerCase();
            return pool;
          });
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

    const sortBy = (key) => {
      sortKeys.value = [key.startsWith("-") ? key.slice(1) : `-${key}`];
    };

    const addSort = (key) => {
      const i = sortKeys.value.indexOf(key);
      const ni = sortKeys.value.indexOf(`-${key}`);
      if (i < 0 && ni < 0) {
        sortKeys.value.push(key);
      } else if (i >= 0) {
        sortKeys.value[i] = `-${key}`;
      } else if (ni >= 0) {
        sortKeys.value.splice(ni, 1);
      }
    };

    const sortData = (data) => {
      if (!data) return [];
      const keys = sortKeys.value;
      return [...data].sort((a, b) => {
        for (const key of keys) {
          const desc = key.startsWith("-");
          const k = desc ? key.slice(1) : key;
          if (a[k] > b[k]) return desc ? -1 : 1;
          if (a[k] < b[k]) return desc ? 1 : -1;
        }
        return 0;
      });
    };

    const orderedPools = computed(() => sortData(pools.value));

    fetch();

    return {
      loading,
      pools,
      sortKeys,
      orderedPools,
      sortBy,
      addSort,
      validSortKeys,
      defaultSortKeys,
    };
  },
});
</script>
