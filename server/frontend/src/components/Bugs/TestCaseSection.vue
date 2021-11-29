<template>
  <div>
    <h3>Testcase</h3>
    <div class="row">
      <div class="form-group col-md-6">
        <input
          type="checkbox"
          id="id_testcase_skip"
          name="testcase_skip"
          v-model="notAttachTest"
        />
        <span>Do not attach a testcase (file {{ mode }} without test).</span>
      </div>
    </div>
    <div v-if="!notAttachTest">
      <div class="alert alert-info" role="alert">
        Testcase will be attached to the {{ mode }}.
      </div>
      <div class="row">
        <div class="form-group col-md-6">
          <label for="testcase_filename">Filename:</label>
          <input
            id="id_testcase_filename"
            class="form-control"
            name="testcase_filename"
            type="text"
            v-model="filename"
          />
        </div>
      </div>
      <div class="row" v-if="!entry.testcase_isbinary">
        <div class="form-group col-md-12">
          <label for="testcase_content">Content:</label>
          <textarea
            id="id_testcase_content"
            class="form-control"
            name="testcase_content"
            type="text"
            :readonly="content === 'Content loading...'"
            v-model="content"
          ></textarea>
        </div>
      </div>
    </div>
    <hr />
  </div>
</template>

<script>
import * as api from "../../api";

export default {
  props: {
    mode: {
      type: String,
      required: false,
      default: "bug",
    },
    initialNotAttachTest: {
      type: Boolean,
      required: false,
      default: false,
    },
    entry: {
      type: Object,
      required: true,
    },
    template: {
      type: Object,
      required: true,
    },
  },
  data: () => ({
    notAttachTest: false,
    filename: "",
    content: "Content loading...",
  }),
  async mounted() {
    this.notAttachTest = this.initialNotAttachTest;
    this.filename = this.template
      ? this.template.testcase_filename
      : this.entry.testcase.split(/[\\/]/).pop();
    if (!this.entry.testcase_isbinary)
      this.content = await api.retrieveCrashTestCase(this.entry.id);
  },
  watch: {
    notAttachTest: function () {
      this.$emit("update-not-attach-test", this.notAttachTest);
    },
    filename: function () {
      if (this.filename) this.$emit("update-filename", this.filename);
      // Prevent removing the whole section when the filename input is empty
      else this.$emit("update-filename", " ");
    },
    content: function () {
      this.$emit("update-content", this.content);
    },
  },
};
</script>

<style scoped></style>
