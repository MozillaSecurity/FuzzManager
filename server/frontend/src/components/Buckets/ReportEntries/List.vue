<template>
  <div class="table-responsive">
    <table class="table table-condensed table-hover table-bordered table-db">
      <thead>
        <tr>
          <th>Reported</th>
          <th>UUID</th>
          <th>URL</th>
          <th>App</th>
          <th>Channel</th>
          <th>Version</th>
          <th>Breakage Category</th>
          <th>OS</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(entry, index) in entries"
          :key="entry.id"
          :class="{ odd: index % 2 === 0, even: index % 2 !== 0 }"
        >
          <td>{{ entry.reported_at | date }}</td>
          <td>
            <a :href="entry.view_url">{{ entry.uuid }}</a>
          </td>
          <td>{{ entry.url }}</td>
          <td>{{ entry.app_name }}</td>
          <td>{{ entry.app_channel }}</td>
          <td>{{ entry.app_version }}</td>
          <td>{{ entry.breakage_category }}</td>
          <td>
            <img
              width="16px"
              height="16px"
              alt="Linux"
              :src="staticLogo('linux')"
              v-if="entry.os === 'Linux'"
            />
            <img
              width="16px"
              height="16px"
              alt="macOS"
              :src="staticLogo('macosx')"
              v-else-if="entry.os === 'Mac'"
            />
            <img
              width="16px"
              height="16px"
              alt="Windows"
              :src="staticLogo('windows')"
              v-else-if="entry.os === 'Windows'"
            />
            <img
              width="16px"
              height="16px"
              alt="Android"
              :src="staticLogo('android')"
              v-else-if="entry.os === 'Android'"
            />
            <template v-else>{{ entry.os }}</template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { date } from "../../../helpers";

export default {
  props: {
    entries: {
      type: Array,
      required: true,
    },
  },
  filters: {
    date: date,
  },
  methods: {
    staticLogo(name) {
      return window.location.origin + "/static/img/os/" + name + ".png";
    },
  },
};
</script>

<style scoped></style>
