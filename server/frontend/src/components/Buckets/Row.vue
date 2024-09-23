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
    <td>
      <activitygraph :data="bucket.report_history" :range="activityRange" />
    </td>
    <td>{{ bucket.size }}</td>
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
      <assignbutton
        v-else-if="canEdit"
        :bucket="bucket.id"
        :providers="providers"
      />
    </td>
  </tr>
</template>

<script>
import AssignBtn from "./AssignBtn.vue";
import ActivityGraph from "../ActivityGraph.vue";

export default {
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
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
