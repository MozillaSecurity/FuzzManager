<template>
  <tr>
    <td>
      <a title="View bucket" :href="bucket.view_url">
        {{ bucket.id }}
      </a>
    </td>
    <td class="wrap-anywhere">
      <span class="two-line-limit">{{ bucket.description }}</span>
    </td>
    <td>{{ bucket.priority }}</td>
    <td>
      <activitygraph :data="bucket.report_history" :range="activityRange" />
    </td>
    <td class="wrap-anywhere">{{ bucket.latest_report | date }}</td>
    <td>
      {{ bucket.size }}
      <span
        v-if="bucket.reassign_in_progress"
        class="bi bi-hourglass"
        data-toggle="tooltip"
        data-placement="top"
        title="Reports are currently being reassigned in this bucket"
      ></span>
    </td>
    <td>
      <a
        v-if="bucket.bug && bucket.bug_urltemplate"
        :class="{ fixedbug: bucket.bug_closed }"
        :href="bucket.bug_urltemplate"
        target="_blank"
      >
        {{ bucket.bug }}
      </a>
      <p v-else-if="bucket.bug">
        {{ bucket.bug }} on {{ bucket.bug_hostname }}
      </p>
      <div v-else-if="canEdit" class="btn-group">
        <assignbutton :bucket="bucket.id" :providers="providers" />
        <a :href="bucket.new_bug_url" class="btn btn-danger">File a bug</a>
      </div>
    </td>
  </tr>
</template>

<script>
import { date } from "../../helpers";
import AssignBtn from "./AssignBtn.vue";
import ActivityGraph from "../ActivityGraph.vue";

export default {
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
  },
  filters: {
    date: date,
  },
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    canEdit: {
      type: Boolean,
      required: true,
    },
    providers: {
      type: Array,
      required: true,
    },
    bucket: {
      type: Object,
      required: true,
    },
  },
  methods: {
    addFilter(key, value) {
      this.$emit("add-filter", key, value);
    },
  },
};
</script>

<style scoped></style>
