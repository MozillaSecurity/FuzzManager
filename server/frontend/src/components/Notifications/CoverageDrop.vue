<template>
  <div class="row override-row">
    <small class="col-md-1">
      Received {{ formatDate(notification.timestamp) }}
    </small>
    <span class="label label-danger">Coverage drop</span>
    <span class="description">
      {{ notification.description }}
    </span>
    <button type="button" class="close" @click="dismiss">
      <span aria-hidden="true" title="Dismiss">&times;</span>
    </button>
    <div class="btn-group pull-right" role="group">
      <a
        v-if="notification.data?.diff_url"
        class="btn btn-default"
        :href="notification.data?.diff_url"
        >View diff</a
      >
      <a class="btn btn-default" :href="notification.actor_url"
        >View collection</a
      >
    </div>
  </div>
</template>

<script>
import { defineComponent } from "vue";
import * as api from "../../api";
import { errorParser, formatClientTimestamp } from "../../helpers";

export default defineComponent({
  name: "CoverageDrop",
  props: {
    notification: {
      type: Object,
      required: true,
    },
  },
  setup(props, { emit }) {
    console.log(JSON.parse(JSON.stringify(props.notification)));
    const dismiss = async () => {
      try {
        await api.dismissNotification(props.notification.id);
        emit("remove-notification", props.notification.id);
      } catch (err) {
        emit(
          "update-dismiss-error",
          `An error occurred while marking notification ${
            props.notification.id
          } as read: ${errorParser(err)}`,
        );
      }
    };

    return {
      dismiss,
    };
  },
  methods: {
    formatDate: formatClientTimestamp,
  },
});
</script>

<style scoped>
.override-row {
  margin-left: 1.5rem;
  margin-right: 1.5rem;
}
.description {
  margin-left: 1.5rem;
  margin-right: 1.5rem;
}
button.close {
  margin-left: 3rem;
}
small {
  padding-left: 0rem;
  padding-right: 0rem;
  margin-right: 1rem;
}
</style>
