<template>
  <div class="table-responsive">
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th>ID</th>
          <th>Date Added</th>
          <th>Short Signature</th>
          <th>Crash Address</th>
          <th>Test Status</th>
          <th>Product</th>
          <th>Version</th>
          <th>Platform</th>
          <th>OS</th>
          <th>Tool</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(entry, index) in entries"
          :key="entry.id"
          :class="{ odd: index % 2 === 0, even: index % 2 !== 0 }"
        >
          <td>
            <a :href="entry.view_url">{{ entry.id }}</a>
          </td>
          <td>{{ entry.created | formatDate }}</td>
          <td>{{ entry.shortSignature }}</td>
          <td>{{ entry.crashAddress }}</td>
          <td>{{ testCaseText(entry) }}</td>
          <td>{{ entry.product }}</td>
          <td>{{ entry.product_version }}</td>
          <td>{{ entry.platform }}</td>
          <td>
            <img
              width="16px"
              height="16px"
              alt="Linux"
              :src="staticLogo(entry.os)"
              v-if="entry.os === 'linux'"
            />
            <img
              width="16px"
              height="16px"
              alt="MacOS"
              :src="staticLogo(entry.os)"
              v-else-if="entry.os === 'macosx'"
            />
            <img
              width="16px"
              height="16px"
              alt="Windows"
              :src="staticLogo(entry.os)"
              v-else-if="entry.os === 'windows'"
            />
            <img
              width="16px"
              height="16px"
              alt="Android"
              :src="staticLogo(entry.os)"
              v-else-if="entry.os === 'android'"
            />
            <template v-else>{{ entry.os }}</template>
          </td>
          <td>{{ entry.tool }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { formatClientTimestamp } from "../../../helpers";

export default {
  props: {
    entries: {
      type: Array,
      required: true,
    },
  },
  filters: {
    formatDate: formatClientTimestamp,
  },
  methods: {
    testCaseText(entry) {
      if (!entry.testcase) return "No test";
      let text = "Q" + entry.testcase_quality + "\n" + entry.testcase_size;
      if (entry.testcase_isbinary) text += "\n    (binary)";
      return text;
    },
    staticLogo(name) {
      return window.location.origin + "/static/img/os/" + name + ".png";
    },
  },
};
</script>

<style scoped></style>
