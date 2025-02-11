<template>
  <button class="btn btn-default" @click="link">Assign an existing bug</button>
</template>

<script>
import swal from "sweetalert";
import { defineComponent, h, ref, render } from "vue";
import { assignExternalBug, errorParser } from "../../helpers";
import AssignBtnForm from "./AssignBtnForm.vue";

export default defineComponent({
  components: {
    AssignBtnForm,
  },
  props: {
    bucket: {
      type: Number,
      default: null,
      required: true,
    },
    providers: {
      type: Array,
      default: null,
      required: true,
    },
  },
  methods: {
    async link() {
      const externalBugId = ref(null);
      const selectedProvider = ref(null);

      // Create a container div for the form
      const container = document.createElement("div");

      // Create the form component with props
      const formCtor = h(AssignBtnForm, {
        providers: this.providers,
        onUpdateBug: (bug) => (externalBugId.value = bug),
        onUpdateProvider: (provider) => (selectedProvider.value = provider),
      });

      // Mount the component to get the actual DOM element
      render(formCtor, container);

      const value = await swal({
        title: "Assign External Bug",
        content: container,
        buttons: true,
      });

      if (value) {
        try {
          const data = await assignExternalBug(
            this.bucket,
            externalBugId.value,
            selectedProvider.value,
          );
          window.location.href = data.url;
        } catch (err) {
          swal("Oops", errorParser(err), "error");
        }
      }
    },
  },
});
</script>
