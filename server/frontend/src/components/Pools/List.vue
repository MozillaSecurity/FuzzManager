<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-card-list"></i> Fuzzing Pools
    </div>
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th
            v-on:click.exact="sortBy('pool_id')"
            v-on:click.ctrl.exact="addSort('pool_id')"
            :class="{
              active:
                sortKeys.includes('pool_id') || sortKeys.includes('-pool_id'),
            }"
            width="25px"
          >
            ID
          </th>
          <th
            v-on:click.exact="sortBy('pool_name_isort')"
            v-on:click.ctrl.exact="addSort('pool_name_isort')"
            :class="{
              active:
                sortKeys.includes('pool_name_isort') ||
                sortKeys.includes('-pool_name_isort'),
            }"
            width="100px"
          >
            Name
          </th>
          <th
            v-on:click.exact="sortBy('running')"
            v-on:click.ctrl.exact="addSort('running')"
            :class="{
              active:
                sortKeys.includes('running') || sortKeys.includes('-running'),
            }"
            width="75px"
          >
            # of Tasks (Running/Requested)
          </th>
          <th
            v-on:click.exact="sortBy('status')"
            v-on:click.ctrl.exact="addSort('status')"
            :class="{
              active:
                sortKeys.includes('status') || sortKeys.includes('-status'),
            }"
            width="150px"
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
                'label-warning':
                  pool.status !== 'idle' && pool.status !== 'healthy',
                'label-success': pool.status === 'healthy',
                'label-danger': pool.status === 'idle',
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
import { E_SERVER_ERROR, multiSort } from "../../helpers";
import * as api from "../../api";

export default {
  mixins: [multiSort],
  data: function () {
    const defaultSortKeys = ["pool_name_isort"];
    const validSortKeys = ["pool_id", "pool_name_isort", "running", "status"];
    return {
      defaultSortKeys: defaultSortKeys,
      loading: true,
      pools: null,
      sortKeys: [...defaultSortKeys],
      validSortKeys: validSortKeys,
    };
  },
  created: function () {
    this.fetch();
  },
  computed: {
    orderedPools: function () {
      return this.sortData(this.pools);
    },
  },
  methods: {
    buildParams() {
      return {
        vue: "1",
      };
    },
    fetch: _throttle(
      async function () {
        this.loading = true;
        try {
          const data = await api.listPools(this.buildParams());
          this.pools = data.results.map((pool) => {
            pool.pool_name_isort = pool.pool_name.toLowerCase();
            return pool;
          });
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
  },
};
</script>
