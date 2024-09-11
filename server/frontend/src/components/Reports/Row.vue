<template>
  <tr>
    <td>
      <a :href="report.view_url">{{ report.id }}</a>
    </td>
    <td class="wrap-normal">{{ report.created | formatDate }}</td>
    <td v-if="report.bucket">
      <a :href="report.sig_view_url">{{ report.bucket }} </a>
    </td>
    <td v-else>
      <span
        v-if="!report.triagedOnce"
        class="bi bi-hourglass"
        data-toggle="tooltip"
        data-placement="top"
        title="This item hasn't been triaged yet by the server."
      ></span>
      <a
        :href="report.sig_new_url"
        data-toggle="tooltip"
        data-placement="top"
        title="Add"
        class="bi bi-tag-fill dimgray"
      ></a>
      <a
        :href="report.find_sigs_url"
        data-toggle="tooltip"
        data-placement="top"
        title="Search"
        class="bi bi-search dimgray"
      ></a>
    </td>
    <td class="wrap-anywhere">
      <span class="two-line-limit">{{ report.shortSignature }}</span>
    </td>
    <td>{{ report.reportAddress }}</td>
    <td v-if="report.testcase">
      {{ report.testcase_size | formatSize }}
    </td>
    <td v-else>N/A</td>
    <td v-if="report.testcase">
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('testcase__quality', report.testcase_quality)"
        >Q{{ report.testcase_quality }}</a
      >
      <i
        title="test is binary"
        class="bi bi-file-binary"
        v-if="report.testcase_isbinary"
      ></i>
    </td>
    <td v-else>N/A</td>
    <td>
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('product__name', report.product)"
        >{{ report.product }}</a
      >
    </td>
    <td class="wrap-anywhere">
      <span class="two-line-limit">
        <a
          title="Add to search"
          class="add-filter"
          v-on:click="addFilter('product__version', report.product_version)"
          >{{ report.product_version }}</a
        >
      </span>
    </td>
    <td>
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('platform__name', report.platform)"
        >{{ report.platform }}</a
      >
    </td>
    <td>
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('os__name', report.os)"
      >
        <img
          v-if="report.os === 'linux'"
          width="16px"
          height="16px"
          alt="Linux"
          :src="staticLogo('linux')"
        />
        <img
          v-else-if="report.os === 'macosx'"
          width="16px"
          height="16px"
          alt="MacOS"
          :src="staticLogo('macosx')"
        />
        <img
          v-else-if="report.os === 'windows'"
          width="16px"
          height="16px"
          alt="Windows"
          :src="staticLogo('windows')"
        />
        <img
          v-else-if="report.os === 'android'"
          width="16px"
          height="16px"
          alt="Android"
          :src="staticLogo('android')"
        />
        <span v-else>{{ report.os }}</span>
      </a>
    </td>
    <td>
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('tool__name', report.tool)"
        >{{ report.tool }}</a
      >
    </td>
  </tr>
</template>

<script>
import { formatClientTimestamp, formatSizeFriendly } from "../../helpers";

export default {
  props: {
    report: {
      type: Object,
      required: true,
    },
  },
  filters: {
    formatDate: formatClientTimestamp,
    formatSize: formatSizeFriendly,
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
