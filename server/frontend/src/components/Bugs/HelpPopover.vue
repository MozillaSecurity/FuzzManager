<template>
  <span>
    <span :id="'help-hint-' + field">
      <i class="glyphicon glyphicon-question-sign"></i>
    </span>
    <b-popover :target="'help-hint-' + field" triggers="hover" placement="top">
      <div class="pop-header">Available substitution variables</div>
      <div class="pop-body">
        <ul>
          <li v-for="v in variables" :key="v">
            <code>{{ v }}</code>
          </li>
        </ul>
        <p>
          Render them using
          <code v-pre>{{ myvariable }}</code> (escaped HTML) or
          <code v-pre>{{{ myvariable }}}</code> (unescaped HTML).
        </p>
        <a class="pull-right" target="_blank" :href="documentationLink">
          See documentation
        </a>
      </div>
    </b-popover>
  </span>
</template>

<script>
export default {
  props: {
    field: {
      type: String,
      required: true,
    },
    variables: {
      type: Array,
      required: true,
    },
    documentationLink: {
      type: String,
      required: true,
    },
  },
};
</script>

<style scoped>
.pop-header {
  padding: 1rem;
  margin-bottom: 0;
  background-color: #f7f7f7;
  border-bottom: 1px solid #ebebeb;
  font-size: 1.5rem;
  font-weight: bold;
}
.pop-body {
  padding: 1rem;
  color: #212529;
}
.pop-body p {
  font-size: 1.25rem;
}
.pop-body a {
  margin-bottom: 1rem;
}
</style>
