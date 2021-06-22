<template>
  <tr>
    <td>
      <a title="View signature" :href="signature.view_url">
        {{ signature.id }}
      </a>
    </td>
    <td>{{ signature.shortDescription }}</td>
    <td>{{ signature.size }}</td>
    <td>{{ signature.quality }}</td>
    <td>
      <a
        v-if="signature.bug && signature.bug_urltemplate"
        :class="{ fixedbug: signature.bug_closed }"
        :href="signature.bug_urltemplate"
        target="_blank"
      >
        {{ signature.bug }}
      </a>
      <p v-else-if="signature.bug">
        {{ signature.bug }} on {{ signature.bug_hostname }}
      </p>
      <a v-else title="Assign an external bug" :href="signature.link_url">
        Assign
      </a>
    </td>
    <td>
      <a
        v-if="signature.optimizedSignature"
        :href="signature.opt_pre_url"
        class="btn btn-default"
      >
        Yes
      </a>
    </td>
  </tr>
</template>

<script>
export default {
  props: {
    signature: {
      type: Object,
      required: true,
    },
  },
  methods: {
    addFilter(key, value) {
      this.$emit("add-filter", key, value);
    },
  },
};
</script>

<style scoped></style>
