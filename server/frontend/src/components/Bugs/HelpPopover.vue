<template>
  <FloatingMenu
    :distance="12"
    :skidding="0"
    :delay="{ show: 100, hide: 100 }"
    placement="auto-start"
    :triggers="['hover']"
    :auto-hide="false"
    class="pop-container"
  >
    <template #popper>
      <div class="popper">
        <div class="pop-header">Available substitution variables</div>
        <div class="pop-body">
          <ul>
            <li v-for="v in variables" :key="v">
              <code>{{ v }}</code>
            </li>
          </ul>
          <p>
            Render them using
            <code v-pre>{{ myvariable }}</code> (escaped HTML) <br />
            or <code v-pre>{{{ myvariable }}}</code> (unescaped HTML).
          </p>
          <a class="pull-right" target="_blank" :href="documentationLink">
            See documentation
          </a>
        </div>
      </div>
    </template>
    <span>
      <i class="bi bi-question-circle-fill"></i>
    </span>
  </FloatingMenu>
</template>

<script>
import { Menu as FloatingMenu } from "floating-vue";
import "floating-vue/dist/style.css";
import { defineComponent } from "vue";

export default defineComponent({
  name: "HelpPopover",
  components: {
    FloatingMenu,
  },
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
  setup() {
    // If you need any reactive logic, put it here
    return {};
  },
});
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
.popper {
  text-align: left;
}
.pop-container {
  display: inline;
  margin-left: 0.5rem;
}
</style>
