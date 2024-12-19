<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-bell-fill"></i>
      Unread notifications
      <span v-if="notifications && notifications.length">
        ({{ currentEntries }}/{{ totalEntries }})
      </span>
      <span
        v-if="notifications && notifications.length"
        class="step-links ml-5"
      >
        <a
          v-show="currentPage > 1"
          class="bi bi-caret-left-fill"
          @click="prevPage"
        ></a>
        <span class="current">
          Page {{ currentPage }} of {{ totalPages }}.
        </span>
        <a
          v-show="currentPage < totalPages"
          data-toggle="tooltip"
          data-placement="top"
          title=""
          class="bi bi-caret-right-fill dimgray"
          data-original-title="Next"
          @click="nextPage"
        ></a>
      </span>
      <a
        v-if="notifications && notifications.length"
        type="button"
        class="text-danger pull-right"
        @click="dismissAll"
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
              @remove-notification="removeNotification($event)"
              @update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
          <template v-else-if="notification.verb === 'coverage_drop'">
            <CoverageDrop
              :notification="notification"
              @remove-notification="removeNotification($event)"
              @update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
          <template v-else-if="notification.verb === 'inaccessible_bug'">
            <InaccessibleBug
              :notification="notification"
              @remove-notification="removeNotification($event)"
              @update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
          <template v-else-if="notification.verb === 'tasks_failed'">
            <TasksFailed
              :notification="notification"
              @remove-notification="removeNotification($event)"
              @update-dismiss-error="dismissError = $event"
            />
            <hr />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, onMounted, ref } from "vue";
import * as api from "../../api";
import { errorParser } from "../../helpers";
import BucketHit from "./BucketHit.vue";
import CoverageDrop from "./CoverageDrop.vue";
import InaccessibleBug from "./InaccessibleBug.vue";
import TasksFailed from "./TasksFailed.vue";

const pageSize = 25;

export default defineComponent({
  name: "Inbox",
  components: {
    BucketHit,
    CoverageDrop,
    InaccessibleBug,
    TasksFailed,
  },
  setup() {
    const notifications = ref(null);
    const error = ref(null);
    const dismissError = ref(null);
    const dismissAllError = ref(null);
    const currentEntries = ref("?");
    const currentPage = ref(1);
    const totalEntries = ref("?");
    const totalPages = ref(1);

    const fetchUnread = async () => {
      try {
        const data = await api.listUnreadNotifications({
          limit: pageSize,
          offset: `${(currentPage.value - 1) * pageSize}`,
        });
        notifications.value = data.results;
        currentEntries.value = notifications.value.length;
        totalEntries.value = data.count;
        totalPages.value = Math.max(
          Math.ceil(totalEntries.value / pageSize),
          1,
        );

        if (currentPage.value > totalPages.value) {
          currentPage.value = totalPages.value;
          await fetchUnread();
          return;
        }
      } catch (err) {
        error.value = errorParser(err);
      }
    };

    const nextPage = async () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++;
        await fetchUnread();
      }
    };

    const prevPage = async () => {
      if (currentPage.value > 1) {
        currentPage.value--;
        await fetchUnread();
      }
    };

    const dismissAll = async () => {
      dismissAllError.value = null;
      try {
        await api.dismissAllNotifications();
        notifications.value = [];
        currentEntries.value = totalEntries.value = 0;
        currentPage.value = totalPages.value = 1;
      } catch (err) {
        dismissAllError.value = errorParser(err);
      }
    };

    const removeNotification = (notification) => {
      notifications.value = notifications.value.filter(
        (n) => n.id !== notification,
      );
      currentEntries.value--;
      totalEntries.value--;
    };

    onMounted(fetchUnread);

    return {
      notifications,
      error,
      dismissError,
      dismissAllError,
      currentEntries,
      currentPage,
      totalEntries,
      totalPages,
      nextPage,
      prevPage,
      dismissAll,
      removeNotification,
    };
  },
});
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
