<template>
  <tr>
    <td>
      <a title="View signature" :href="signature.view_url">
        {{ signature.id }}
      </a>
    </td>
    <td class="wrap-anywhere">
      <span class="two-line-limit">{{ signature.shortDescription }}</span>
    </td>
    <td>
      <activitygraph :data="signature.crash_history" :range="activityRange" />
    </td>
    <td>
      {{ signature.size }}
      <span
        v-if="signature.reassign_in_progress"
        class="bi bi-hourglass-split"
        data-toggle="tooltip"
        data-placement="top"
        title="Crashes are currently being reassigned in this bucket"
      ></span>
    </td>
    <td v-if="loadingQuality">
      <ClipLoader class="m-strong align-def" :color="'black'" :size="'12px'" />
    </td>
    <td v-else>{{ signature.best_quality }}</td>
    <td>
      <a
        v-if="signature.bug && signature.bug_urltemplate"
        :class="{ fixedbug: signature.bug_closed }"
        :href="signature.bug_urltemplate"
        target="_blank"
      >
        {{ signature.bug }}
      </a>
      <p v-else-if="signature.bug">
        {{ signature.bug }} on {{ signature.bug_hostname }}
      </p>
      <assignbutton v-else :bucket="signature.id" :providers="providers" />
    </td>
    <td>
      <a
        v-if="signature.has_optimization"
        :href="signature.opt_pre_url"
        class="btn btn-default"
      >
        Yes
      </a>
    </td>
  </tr>
</template>

<script>
import ClipLoader from "vue-spinner/src/ClipLoader.vue";
import AssignBtn from "./AssignBtn.vue";
import ActivityGraph from "../ActivityGraph.vue";

export default {
  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
    ClipLoader,
  },
  props: {
    activityRange: {
      type: Number,
      required: true,
    },
    loadingQuality: {
      type: Boolean,
      required: true,
    },
    providers: {
      type: Array,
      required: true,
    },
    signature: {
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

<style scoped>
.align-def {
  text-align: revert;
}
</style>
