<template>
  <div class="row override-row">
    <small class="col-md-1">
      Received {{ formatDate(notification.timestamp) }}
    </small>
    <span class="label label-info">Bucket hit</span>
    <span class="description">
      {{ notification.description }}
    </span>
    <button type="button" class="close" @click="dismiss">
      <span aria-hidden="true" title="Dismiss">&times;</span>
    </button>
    <div class="btn-group pull-right" role="group">
      <a class="btn btn-default" :href="notification.actor_url">View bucket</a>
      <a class="btn btn-info" :href="notification.target_url">
        View new crash entry
      </a>
    </div>
  </div>
</template>

<script>
import { defineComponent } from "vue";
import * as api from "../../api";
import { errorParser, formatClientTimestamp } from "../../helpers";

export default defineComponent({
  name: "BucketHit",
  props: {
    notification: {
      type: Object,
      required: true,
    },
  },
  setup(props, { emit }) {
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
