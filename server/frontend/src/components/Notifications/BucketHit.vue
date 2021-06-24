<template>
  <div class="row override-row">
    <span class="label label-info">Bucket hit</span>
    <span class="description">
      {{ notification.description }}
    </span>
    <button type="button" class="close" title="Dismiss (do nothing for now)">
      <span aria-hidden="true">&times;</span>
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
export default {
  props: {
    notification: {
      type: Object,
      required: true,
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
</style>
