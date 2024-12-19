<template>
  <div>
    <h3>Crash data</h3>
    <div class="row">
      <div class="form-group col-md-6">
        <input
          id="id_crashdata_skip"
          v-model="notAttachData"
          type="checkbox"
          name="crashdata_skip"
        />
        <span>Do not attach crash data.</span>
      </div>
    </div>
    <div v-if="!notAttachData">
      <div class="alert alert-info" role="alert">
        Crash data will be attached to the {{ mode }}.
      </div>
      <div class="row">
        <div class="form-group col-md-12">
          <label for="crashdata_attach">Content:</label>
          <textarea
            id="id_crashdata_attach"
            v-model="data"
            class="form-control"
            name="crashdata_attach"
            type="text"
          ></textarea>
        </div>
      </div>
    </div>
    <hr />
  </div>
</template>

<script>
import { defineComponent, ref, watch, onMounted } from "vue";

export default defineComponent({
  name: "CrashDataSection",
  props: {
    mode: {
      type: String,
      required: false,
      default: "bug",
    },
    initialNotAttachData: {
      type: Boolean,
      required: false,
      default: false,
    },
    initialData: {
      type: String,
      required: true,
    },
    pathPrefix: {
      type: String,
      required: false,
      default: null,
    },
  },
  emits: ["update-not-attach-data", "update-data"],
  setup(props, { emit }) {
    const notAttachData = ref(false);
    const data = ref("");

    onMounted(() => {
      notAttachData.value = props.initialNotAttachData;
      data.value = props.initialData;
    });

    watch(notAttachData, (newValue) => {
      emit("update-not-attach-data", newValue);
    });

    watch(data, (newValue) => {
      if (props.pathPrefix) {
        data.value = newValue.replaceAll(props.pathPrefix, "");
      }
      emit("update-data", data.value);
    });

    return {
      notAttachData,
      data,
    };
  },
});
</script>

<style scoped></style>
