<template>
  <tr>
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
        v-on:click="addFilter('testcase__quality', crash.testcase_quality)"
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
</template>

<script>
import { formatClientTimestamp } from "../../helpers";

export default {
  props: {
    crash: {
      type: Object,
      required: true,
    },
  },
  filters: {
    formatDate: formatClientTimestamp,
  },
  methods: {
    addFilter(key, value) {
      this.$emit("add-filter", key, value);
    },
    staticLogo(name) {
      return window.location.origin + "/static/img/os/" + name + ".png";
    },
  },
};
</script>

<style scoped>
.add-filter {
  cursor: cell;
}
.dimgray {
  color: dimgray;
}
</style>
