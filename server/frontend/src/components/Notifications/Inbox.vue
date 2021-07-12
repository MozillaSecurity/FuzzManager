<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="glyphicon glyphicon-bell"></i> Unread notifications
      <a
        v-if="notifications && notifications.length"
        type="button"
        class="text-danger pull-right"
        v-on:click="dismissAll"
      >
        Dismiss all notifications
      </a>
    </div>
    <div class="panel-body">
      <div v-if="error" class="alert alert-danger" role="alert">
        An error occurred while fetching unread notifications: {{ error }}
      </div>
      <div v-if="dismissError" class="alert alert-danger mb-2" role="alert">
        {{ dismissError }}
      </div>
      <div v-if="dismissAllError" class="alert alert-danger mb-2" role="alert">
        An error occurred while marking all notifications as read:
        {{ dismissAllError }}
      </div>
      <div v-if="notifications">
        <div v-if="!notifications.length">
          <div class="alert alert-info" role="alert">
            No unread notification.
          </div>
        </div>
        <div v-for="(notification, index) in notifications" :key="index">
          <template v-if="notification.verb === 'bucket_hit'">
            <BucketHit
              :notification="notification"
              v-on:remove-notification="
                notifications = notifications.filter((n) => n.id !== $event)
              "
              v-on:update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
          <template v-else-if="notification.verb === 'inaccessible_bug'">
            <InaccessibleBug
              :notification="notification"
              v-on:remove-notification="
                notifications = notifications.filter((n) => n.id !== $event)
              "
              v-on:update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { errorParser } from "../../helpers";
import * as api from "../../api";
import BucketHit from "./BucketHit.vue";
import InaccessibleBug from "./InaccessibleBug.vue";

export default {
  components: {
    BucketHit,
    InaccessibleBug,
  },
  data: () => ({
    notifications: null,
    error: null,
    dismissError: null,
    dismissAllError: null,
  }),
  async created() {
    try {
      const data = await api.listUnreadNotifications();
      this.notifications = data.results;
    } catch (err) {
      this.error = errorParser(err);
    }
  },
  methods: {
    async dismissAll() {
      this.dismissAllError = null;
      try {
        await api.dismissAllNotifications();
        this.notifications = [];
      } catch (err) {
        this.dismissAllError = errorParser(err);
      }
    },
  },
};
</script>

<style scoped>
div.panel-body {
  padding-top: 2rem;
  padding-bottom: 2rem;
}
.mb-2 {
  margin-bottom: 2rem !important;
}
div.alert {
  margin-bottom: 0;
}
:last-child > hr {
  display: none;
}
</style>
