<template>
  <div id="main" class="panel panel-default">
    <div class="panel-heading">
      <i class="glyphicon glyphicon-tasks"></i> Fuzzing Pools
    </div>
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th
            v-on:click="sortBy('pool_id')"
            :class="{ active: sortKey === 'pool_id' }"
            width="25px"
          >
            ID
          </th>
          <th
            v-on:click="sortBy('pool_name')"
            :class="{ active: sortKey === 'pool_name' }"
            width="100px"
          >
            Name
          </th>
          <th
            v-on:click="sortBy('running')"
            :class="{ active: sortKey === 'running' }"
            width="75px"
          >
            # of Tasks (Running/Requested)
          </th>
          <th
            v-on:click="sortBy('status')"
            :class="{ active: sortKey === 'status' }"
            width="150px"
          >
            Status
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pool in ordered_pools" :key="pool.id">
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
import _orderBy from "lodash/orderBy";
import sweetAlert from "sweetalert";
import { errorParser, E_SERVER_ERROR } from "../../helpers";
import * as api from "../../api";

const defaultReverse = false;
const defaultSortKey = "pool_name";

export default {
  data: function () {
    return {
      loading: true,
      pools: null,
      reverse: defaultReverse,
      sortKey: defaultSortKey,
      timer: "",
    };
  },
  created: function () {
    this.fetch();
    this.timer = setInterval(this.fetch, 60000);
  },
  beforeDestroy: function () {
    clearInterval(this.timer);
  },
  computed: {
    ordered_pools: function () {
      return _orderBy(
        this.pools,
        [this.sortKey],
        [this.reverse ? "desc" : "asc"]
      );
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
          this.pools = data.results;
        } catch (err) {
          if (
            err.response &&
            err.response.status === 400 &&
            err.response.data
          ) {
            // eslint-disable-next-line no-console
            console.debug(err.response.data);
            sweetAlert("Oops", E_SERVER_ERROR, "error");
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
    sortBy: function (sortKey) {
      this.reverse = this.sortKey === sortKey ? !this.reverse : false;
      this.sortKey = sortKey;
    },
  },
};
</script>
