<template>
  <div class="row override-row">
    <small class="col-md-1">
      Received {{ notification.timestamp | formatDate }}
    </small>
    <span class="label label-info">Bucket hit</span>
    <span class="description">
      {{ notification.description }}
    </span>
    <button type="button" class="close" v-on:click="dismiss">
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
import { errorParser, formatClientTimestamp } from "../../helpers";
import * as api from "../../api";

export default {
  props: {
    notification: {
      type: Object,
      required: true,
    },
  },
  filters: {
    formatDate: formatClientTimestamp,
  },
  methods: {
    async dismiss() {
      try {
        await api.dismissNotification(this.notification.id);
        this.$emit("remove-notification", this.notification.id);
      } catch (err) {
        this.$emit(
          "update-dismiss-error",
          `An error occurred while marking notification ${
            this.notification.id
          } as read: ${errorParser(err)}`
        );
      }
    },
  },
};
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
