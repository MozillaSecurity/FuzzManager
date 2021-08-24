<template>
  <Popper trigger="hover" :options="{ placement: 'right' }">
    <div class="popper">
      <div class="pop-header">Available query parameters</div>
      <div class="pop-body">
        <h4>
          Available parameters
          <button
            class="btn btn-default btn-xs pull-right ml-8"
            v-on:click="showParams = !showParams"
          >
            <i class="glyphicon glyphicon-minus" v-if="showParams"></i>
            <i class="glyphicon glyphicon-plus" v-else></i>
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
          Usable operations
          <button
            class="btn btn-default btn-xs pull-right ml-8"
            v-on:click="showOps = !showOps"
          >
            <i class="glyphicon glyphicon-minus" v-if="showOps"></i>
            <i class="glyphicon glyphicon-plus" v-else></i>
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
            href="https://docs.djangoproject.com/fr/3.2/ref/models/querysets/#field-lookups"
          >
            More operations
          </a>
        </div>
      </div>
    </div>
    <!-- eslint-disable-next-line -->
    <span slot="reference">
      <i class="glyphicon glyphicon-question-sign"></i>
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
