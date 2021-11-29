<template>
  <Popper trigger="hover" :options="{ placement: 'right' }">
    <div class="popper">
      <div class="pop-header">Advanced Query</div>
      <div class="pop-body">
        <h4>
          Query Structure
          <button
            class="btn btn-default btn-xs pull-right ml-8"
            v-on:click="showQuery = !showQuery"
          >
            <i class="bi bi-dash" v-if="showQuery"></i>
            <i class="bi bi-plus" v-else></i>
          </button>
        </h4>
        <div class="pop-list mt-1" v-if="showQuery">
          <p>
            Queries are JSON objects representing an SQL
            <code>WHERE</code> clause. Each query object can have these
            key/values:
          </p>
          <ul>
            <li>
              <code>op</code> (required), the logical operation to apply between
              other key/values in this object. Value must be one of:
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
            v-on:click="showParams = !showParams"
          >
            <i class="bi bi-dash" v-if="showParams"></i>
            <i class="bi bi-plus" v-else></i>
          </button>
        </h4>
        <div class="pop-list mt-1" v-if="showParams">
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
            v-on:click="showOps = !showOps"
          >
            <i class="bi bi-dash" v-if="showOps"></i>
            <i class="bi bi-plus" v-else></i>
          </button>
        </h4>
        <div class="pop-list mt-1" v-if="showOps">
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
    <!-- eslint-disable-next-line -->
    <span slot="reference">
      <i class="bi bi-question-circle-fill"></i>
    </span>
  </Popper>
</template>

<script>
import Popper from "vue-popperjs";

export default {
  components: {
    Popper,
  },
  props: {
    parameters: {
      type: Array,
      required: true,
    },
  },
  data: () => ({
    showQuery: true,
    showParams: true,
    showOps: false,
  }),
};
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
</style>
