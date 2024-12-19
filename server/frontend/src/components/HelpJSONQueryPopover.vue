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
        <div class="pop-header">Advanced Query</div>
        <div class="pop-body">
          <h4>
            Query Structure
            <button
              class="btn btn-default btn-xs pull-right ml-8"
              @click="showQuery = !showQuery"
            >
              <i v-if="showQuery" class="bi bi-dash"></i>
              <i v-else class="bi bi-plus"></i>
            </button>
          </h4>
          <div v-if="showQuery" class="pop-list mt-1">
            <p>
              Queries are JSON objects representing an SQL
              <code>WHERE</code> clause. Each query object can have these
              key/values:
            </p>
            <ul>
              <li>
                <code>op</code> (required), the logical operation to apply
                between other key/values in this object. Value must be one of:
                <code>AND</code>, <code>OR</code>, or
                <code>NOT</code>
              </li>
              <li>
                available parameters (below), with an appropriate value type
              </li>
              <li>sub-query objects as value (key is ignored)</li>
            </ul>
            <p>
              <code>NOT</code> operations must have exactly one other key/value
              specified.
            </p>
          </div>
          <h4>
            Available parameters
            <button
              class="btn btn-default btn-xs pull-right ml-8"
              @click="showParams = !showParams"
            >
              <i v-if="showParams" class="bi bi-dash"></i>
              <i v-else class="bi bi-plus"></i>
            </button>
          </h4>
          <div v-if="showParams" class="pop-list mt-1">
            <p v-for="param in parameters" :key="param.name">
              <code>{{ param.name }}</code>
              : {{ param.type }}
            </p>
          </div>
          <hr />
          <h4>
            Parameter suffixes
            <button
              class="btn btn-default btn-xs pull-right ml-8"
              @click="showOps = !showOps"
            >
              <i v-if="showOps" class="bi bi-dash"></i>
              <i v-else class="bi bi-plus"></i>
            </button>
          </h4>
          <div v-if="showOps" class="pop-list mt-1">
            <p><code>__contains</code>: String</p>
            <p><code>__in</code>: Iterable</p>
            <p><code>__gt</code>: Integer</p>
            <p><code>__gte</code>: Integer</p>
            <p><code>__lt</code>: Integer</p>
            <p><code>__lte</code>: Integer</p>
            <p><code>__startswith</code>: String</p>
            <p><code>__endswith</code>: String</p>
            <p><code>__isnull</code>: Boolean</p>
            <a
              class="pull-right"
              target="_blank"
              href="https://docs.djangoproject.com/en/3.2/ref/models/querysets/#field-lookups"
            >
              More suffixes
            </a>
          </div>
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
  name: "HelpJSONQueryPopover",
  components: {
    FloatingMenu,
  },
  props: {
    parameters: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      showQuery: true,
      showParams: true,
      showOps: false,
    };
  },
});
</script>

<style scoped>
.ml-8 {
  margin-left: 8rem;
}
.mt-1 {
  margin-top: 1rem;
}
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
.pop-body a {
  margin-bottom: 1rem;
}
.pop-list p {
  margin-bottom: 0.25rem;
}
.popper {
  text-align: left;
}
.pop-container {
  display: inline;
  margin-left: 0.5rem;
}
</style>
