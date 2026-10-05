<template>
  <div>
    <h3>Testcase</h3>
    <div class="row">
      <div class="form-group col-md-6">
        <label class="testcase-option" for="id_testcase_skip">
          <input
            id="id_testcase_skip"
            v-model="notAttachTest"
            type="checkbox"
            name="testcase_skip"
            :disabled="disabled"
          />
          Do not attach a testcase (file {{ mode }} without test).
        </label>
      </div>
    </div>
    <div v-if="!notAttachTest">
      <div v-if="isZip" class="row">
        <div class="form-group col-md-6">
          <label class="testcase-option" for="id_testcase_unpack">
            <input
              id="id_testcase_unpack"
              v-model="unpackArchive"
              type="checkbox"
              :disabled="disabled"
              @change="onUnpackChange"
            />
            Unpack zip archive
          </label>
        </div>
      </div>
      <div v-if="loading" role="status">
        Loading {{ unpackArchive ? "ZIP archive" : "testcase" }}...
      </div>
      <div v-if="error" class="alert alert-danger" role="alert">
        {{ error }}
        <button
          type="button"
          class="btn btn-default"
          :disabled="disabled || loading"
          @click="retryDownload"
        >
          Retry
        </button>
      </div>
      <div class="archive-files">
        <p class="archive-count" aria-live="polite">
          {{ attachedFilesCount }} of {{ files.length }} files will be attached
        </p>
        <TestcaseFileCard
          v-for="(file, index) in files"
          :key="`${unpackArchive}-${index}`"
          :file="file"
          :index="index"
          :single="!unpackArchive"
          :disabled="disabled || loading"
          @update:basename="onBasenameChange(file, $event)"
          @update:text="onTextChange(file, $event)"
          @update:do-not-attach="onSkipChange(file, $event)"
        />
      </div>
    </div>
    <hr />
  </div>
</template>

<script>
import { computed, defineComponent, markRaw, onMounted, ref, watch } from "vue";
import * as api from "../../api";
import { errorParser } from "../../helpers";
import { loadTestcaseArchive } from "../../testcase_archive";
import { createTestcaseFile } from "../../testcase_files";
import TestcaseFileCard from "./TestcaseFileCard.vue";

export default defineComponent({
  name: "TestCaseSection",
  components: { TestcaseFileCard },
  props: {
    mode: { type: String, default: "bug" },
    disabled: { type: Boolean, default: false },
    initialNotAttachTest: { type: Boolean, default: false },
    entry: { type: Object, required: true },
    template: { type: Object, required: true },
    fileExtension: { type: String, default: null },
    fileName: { type: String, required: true },
  },
  emits: [
    "update-not-attach-test",
    "update-filename",
    "update-content",
    "update-files",
  ],
  setup(props, { emit }) {
    const notAttachTest = ref(props.initialNotAttachTest);
    const unpackArchive = ref(false);
    const singleFile = ref({
      originalName: props.entry.testcase?.split(/[\\/]/).pop() || "testcase",
      basename: props.fileName,
      extension: props.fileExtension,
      bytes: null,
      text: null,
      originalText: null,
      doNotAttach: false,
    });
    const singleLoading = ref(true);
    const singleError = ref(null);
    const archiveFiles = ref([]);
    const archiveLoading = ref(false);
    const archiveError = ref(null);
    const isZip = computed(() => /\.zip$/i.test(props.entry.testcase || ""));
    const files = computed(() =>
      unpackArchive.value ? archiveFiles.value : [singleFile.value],
    );
    const loading = computed(() =>
      unpackArchive.value ? archiveLoading.value : singleLoading.value,
    );
    const error = computed(() =>
      unpackArchive.value ? archiveError.value : singleError.value,
    );
    const attachedFilesCount = computed(
      () => files.value.filter((file) => !file.doNotAttach).length,
    );
    const emitFiles = () =>
      emit("update-files", {
        files: files.value,
        loading: loading.value,
        error: error.value,
      });
    let source;
    const sourceBytes = () =>
      (source ||= api
        .retrieveCrashTestCaseBinary(props.entry.id)
        .catch((error) => {
          source = null;
          throw error;
        }));
    const setSingleContent = (bytes) => {
      const file = createTestcaseFile(
        props.entry.testcase || "testcase",
        bytes,
        !props.entry.testcase_isbinary,
      );
      // Keep the selected template's basename and any per-file choices.
      Object.assign(singleFile.value, {
        bytes: markRaw(file.bytes),
        text: file.text,
        originalText: file.originalText,
      });
      singleError.value = null;
      emit("update-content", file.text ?? "");
    };
    const loadSingleFile = async () => {
      if (singleLoading.value) return;
      singleLoading.value = true;
      singleError.value = null;
      emitFiles();
      try {
        setSingleContent(await sourceBytes());
      } catch (error) {
        singleError.value = `Unable to load testcase contents: ${errorParser(error)}`;
      } finally {
        singleLoading.value = false;
        emitFiles();
      }
    };
    const onUnpackChange = async () => {
      if (!unpackArchive.value || archiveFiles.value.length) {
        emitFiles();
        return;
      }
      if (archiveLoading.value) {
        emitFiles();
        return;
      }
      archiveLoading.value = true;
      archiveError.value = null;
      emitFiles();
      try {
        const bytes = await sourceBytes();
        if (singleError.value) setSingleContent(bytes);
        archiveFiles.value = (
          await loadTestcaseArchive(props.entry.id, bytes)
        ).map((file) => ({ ...file, bytes: markRaw(file.bytes) }));
      } catch (error) {
        archiveError.value = `Unable to unpack ZIP archive: ${errorParser(error)}`;
      } finally {
        archiveLoading.value = false;
        emitFiles();
      }
    };
    const onBasenameChange = (file, value) => {
      file.basename = value;
      if (!unpackArchive.value) emit("update-filename", value);
      emitFiles();
    };
    const onTextChange = (file, value) => {
      file.text = value;
      if (!unpackArchive.value) emit("update-content", value);
      emitFiles();
    };
    const onSkipChange = (file, value) => {
      file.doNotAttach = value;
      emitFiles();
    };
    watch(
      () => [props.fileName, props.fileExtension],
      ([basename, extension]) => {
        singleFile.value.basename = basename;
        singleFile.value.extension = extension;
        emitFiles();
      },
    );
    watch(notAttachTest, (value) => emit("update-not-attach-test", value));
    const retryDownload = () =>
      unpackArchive.value ? onUnpackChange() : loadSingleFile();
    onMounted(() => {
      singleLoading.value = false;
      return loadSingleFile();
    });
    return {
      notAttachTest,
      unpackArchive,
      isZip,
      files,
      loading,
      error,
      attachedFilesCount,
      onUnpackChange,
      retryDownload,
      onBasenameChange,
      onTextChange,
      onSkipChange,
    };
  },
});
</script>

<style scoped>
.testcase-option {
  font-weight: normal;
}
.testcase-option input {
  margin-right: 5px;
}
.archive-files {
  margin-bottom: 16px;
}
.archive-count {
  color: #667085;
  margin: 0 0 12px;
}
</style>
