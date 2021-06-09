<template>
  <div>
    <h3>Crash data</h3>
    <div class="row">
      <div class="form-group col-md-6">
        <input
          type="checkbox"
          id="id_crashdata_skip"
          name="crashdata_skip"
          v-model="notAttachData"
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
            class="form-control"
            name="crashdata_attach"
            type="text"
            v-model="data"
          ></textarea>
        </div>
      </div>
    </div>
    <hr />
  </div>
</template>

<script>
export default {
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
  data: () => ({
    notAttachData: false,
    data: "",
  }),
  async mounted() {
    this.notAttachData = this.initialNotAttachData;
    this.data = this.initialData;
  },
  watch: {
    notAttachData: function () {
      this.$emit("update-not-attach-data", this.notAttachData);
    },
    data: function () {
      if (this.pathPrefix) {
        this.data = this.data.replaceAll(this.pathPrefix, "");
      }
      this.$emit("update-data", this.data);
    },
  },
};
</script>

<style scoped></style>
