<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-bell-fill"></i>
      Unread notifications
      <span v-if="notifications && notifications.length">
        ({{ currentEntries }}/{{ totalEntries }})
      </span>
      <span
        class="step-links ml-5"
        v-if="notifications && notifications.length"
      >
        <a
          v-on:click="prevPage"
          v-show="currentPage > 1"
          class="bi bi-caret-left-fill"
        ></a>
        <span class="current">
          Page {{ currentPage }} of {{ totalPages }}.
        </span>
        <a
          v-on:click="nextPage"
          v-show="currentPage < totalPages"
          data-toggle="tooltip"
          data-placement="top"
          title=""
          class="bi bi-caret-right-fill dimgray"
          data-original-title="Next"
        ></a>
      </span>
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
              v-on:remove-notification="removeNotification($event)"
              v-on:update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
          <template v-else-if="notification.verb === 'inaccessible_bug'">
            <InaccessibleBug
              :notification="notification"
              v-on:remove-notification="removeNotification($event)"
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

const pageSize = 25;

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
    currentEntries: "?",
    currentPage: 1,
    totalEntries: "?",
    totalPages: 1,
  }),
  async created() {
    await this.fetchUnread();
  },
  methods: {
    async fetchUnread() {
      try {
        const data = await api.listUnreadNotifications({
          limit: pageSize,
          offset: `${(this.currentPage - 1) * pageSize}`,
        });
        this.notifications = data.results;
        this.currentEntries = this.notifications.length;
        this.totalEntries = data.count;
        this.totalPages = Math.max(Math.ceil(this.totalEntries / pageSize), 1);
        if (this.currentPage > this.totalPages) {
          this.currentPage = this.totalPages;
          await this.fetchUnread();
          return;
        }
      } catch (err) {
        this.error = errorParser(err);
      }
    },
    async nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        await this.fetchUnread();
      }
    },
    async prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--;
        await this.fetchUnread();
      }
    },
    async dismissAll() {
      this.dismissAllError = null;
      try {
        await api.dismissAllNotifications();
        this.notifications = [];
        this.currentEntries = this.totalEntries = 0;
        this.currentPage = this.totalPages = 1;
      } catch (err) {
        this.dismissAllError = errorParser(err);
      }
    },
    removeNotification(notification) {
      this.notifications = this.notifications.filter(
        (n) => n.id !== notification
      );
      this.currentEntries--;
      this.totalEntries--;
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
.ml-5 {
  margin-left: 5rem;
}
div.alert {
  margin-bottom: 0;
}
:last-child > hr {
  display: none;
}
</style>
