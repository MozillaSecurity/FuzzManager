<template>
  <div>
    <h3>Testcase</h3>
    <div class="row">
      <div class="form-group col-md-6">
        <input
          id="id_testcase_skip"
          v-model="notAttachTest"
          type="checkbox"
          name="testcase_skip"
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
          <label for="id_testcase_filename">Testcase basename:</label>
          <input
            id="id_testcase_filename"
            v-model="filename"
            class="form-control"
            name="testcase_filename"
            type="text"
          />
        </div>
        <div class="col-md-2">
          <label for="file_extension">File extension:</label>

          <input
            id="file_extension"
            type="text"
            class="form-control"
            disabled
            :value="fileExtension"
          />
        </div>
      </div>
      <div v-if="!entry.testcase_isbinary" class="row">
        <div class="form-group col-md-12">
          <label for="testcase_content">Content:</label>
          <textarea
            id="id_testcase_content"
            v-model="content"
            class="form-control"
            name="testcase_content"
            type="text"
            :readonly="content === 'Content loading...'"
          ></textarea>
        </div>
      </div>
    </div>
    <hr />
  </div>
</template>

<script>
import { computed, defineComponent, onMounted, ref, watch } from "vue";
import * as api from "../../api";

export default defineComponent({
  name: "TestCaseSection",

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
    fileExtension: {
      type: String,
      default: null,
    },
    fileName: {
      type: String,
      required: true,
    },
  },

  emits: ["update-not-attach-test", "update-filename", "update-content"],
  setup(props, { emit }) {
    const notAttachTest = ref(false);
    const filename = computed({
      get: () => props.fileName,
      set: (value) => emit("update-filename", value),
    });
    const content = ref("Content loading...");

    onMounted(async () => {
      notAttachTest.value = props.initialNotAttachTest;

      if (!props.entry.testcase_isbinary) {
        content.value = await api.retrieveCrashTestCase(props.entry.id);
      }
    });

    // Watch handlers
    watch(notAttachTest, (newValue) => {
      emit("update-not-attach-test", newValue);
    });

    watch(content, (newValue) => {
      emit("update-content", newValue);
    });

    return {
      notAttachTest,
      filename,
      content,
    };
  },
});
</script>

<style scoped></style>
