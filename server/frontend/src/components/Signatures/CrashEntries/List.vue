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
          <td>{{ formatDate(entry.created) }}</td>
          <td>{{ entry.shortSignature }}</td>
          <td>{{ entry.crashAddress }}</td>
          <td>{{ testCaseText(entry) }}</td>
          <td>{{ entry.product }}</td>
          <td>{{ entry.product_version }}</td>
          <td>{{ entry.platform }}</td>
          <td>
            <img
              v-if="entry.os === 'linux'"
              width="16px"
              height="16px"
              alt="Linux"
              :src="staticLogo(entry.os)"
            />
            <img
              v-else-if="entry.os === 'macosx'"
              width="16px"
              height="16px"
              alt="MacOS"
              :src="staticLogo(entry.os)"
            />
            <img
              v-else-if="entry.os === 'windows'"
              width="16px"
              height="16px"
              alt="Windows"
              :src="staticLogo(entry.os)"
            />
            <img
              v-else-if="entry.os === 'android'"
              width="16px"
              height="16px"
              alt="Android"
              :src="staticLogo(entry.os)"
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
import { defineComponent } from "vue";
import { formatClientTimestamp } from "../../../helpers";

export default defineComponent({
  name: "CrashEntriesList",
  props: {
    entries: {
      type: Array,
      required: true,
    },
  },
  setup() {
    const testCaseText = (entry) => {
      if (!entry.testcase) return "No test";
      let text = "Q" + entry.testcase_quality + "\n" + entry.testcase_size;
      if (entry.testcase_isbinary) text += "\n    (binary)";
      return text;
    };

    const staticLogo = (name) => {
      return window.location.origin + "/static/img/os/" + name + ".png";
    };

    return {
      testCaseText,
      staticLogo,
    };
  },
  methods: {
    formatDate: formatClientTimestamp,
  },
});
</script>

<style scoped></style>
