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
    <td>{{ signature.best_quality }}</td>
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
import { defineComponent } from "vue";
import ActivityGraph from "../ActivityGraph.vue";
import AssignBtn from "./AssignBtn.vue";

export default defineComponent({
  name: "SignatureRow",

  components: {
    activitygraph: ActivityGraph,
    assignbutton: AssignBtn,
  },

  props: {
    activityRange: {
      type: Number,
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

  emits: ["add-filter"],

  setup(props, { emit }) {
    const addFilter = (key, value) => {
      emit("add-filter", key, value);
    };

    return {
      addFilter,
    };
  },
});
</script>

<style scoped></style>
