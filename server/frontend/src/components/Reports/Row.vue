<template>
  <tr>
    <td class="wrap-normal">{{ report.reported_at | date }}</td>
    <td>
      <a :href="report.view_url">{{ report.uuid }}</a>
    </td>
    <td v-if="report.bucket">
      <a :href="report.sig_view_url">{{ report.bucket }}</a>
    </td>
    <td v-else>
      <span
        class="bi bi-hourglass-split"
        data-toggle="tooltip"
        data-placement="top"
        title="This item hasn't been triaged yet by the server."
      ></span>
    </td>
    <td class="wrap-anywhere">
      <span class="two-line-limit">{{ report.url }}</span>
    </td>
    <td>
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('app__name', report.app_name)"
        >{{ report.app_name }}</a
      >
    </td>
    <td>
      <span class="two-line-limit">
        <a
          title="Add to search"
          class="add-filter"
          v-on:click="addFilter('app__channel', report.app_channel)"
          >{{ report.app_channel }}</a
        >
      </span>
    </td>
    <td>
      <span class="two-line-limit">
        <a
          title="Add to search"
          class="add-filter"
          v-on:click="addFilter('app__version', report.app_version)"
          >{{ report.app_version }}</a
        >
      </span>
    </td>
    <td>
      <span class="two-line-limit">
        <a
          title="Add to search"
          class="add-filter"
          v-on:click="
            addFilter('breakage_category__value', report.breakage_category)
          "
          >{{ report.breakage_category }}</a
        >
      </span>
    </td>
    <td>
      <a
        title="Add to search"
        class="add-filter"
        v-on:click="addFilter('os__name', report.os)"
      >
        <img
          v-if="report.os === 'Linux'"
          width="16px"
          height="16px"
          alt="Linux"
          :src="staticLogo('linux')"
        />
        <img
          v-else-if="report.os === 'Mac'"
          width="16px"
          height="16px"
          alt="macOS"
          :src="staticLogo('macosx')"
        />
        <img
          v-else-if="report.os === 'Windows'"
          width="16px"
          height="16px"
          alt="Windows"
          :src="staticLogo('windows')"
        />
        <img
          v-else-if="report.os === 'Android'"
          width="16px"
          height="16px"
          alt="Android"
          :src="staticLogo('android')"
        />
        <span v-else>{{ report.os }}</span>
      </a>
    </td>
  </tr>
</template>

<script>
import { date, formatSizeFriendly } from "../../helpers";

export default {
  props: {
    report: {
      type: Object,
      required: true,
    },
  },
  filters: {
    date: date,
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
  cursor: zoom-in;
}
.dimgray {
  color: dimgray;
}
</style>
