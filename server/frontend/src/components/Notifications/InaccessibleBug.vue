<template>
  <div class="row override-row">
    <span class="label label-danger">Inaccessible bug</span>
    <span class="description">
      {{ notification.description }}
    </span>
    <button type="button" class="close" title="Dismiss (do nothing for now)">
      <span aria-hidden="true">&times;</span>
    </button>
    <a
      class="btn btn-info pull-right"
      :href="notification.external_bug_url"
      target="_blank"
    >
      View external bug
    </a>
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
