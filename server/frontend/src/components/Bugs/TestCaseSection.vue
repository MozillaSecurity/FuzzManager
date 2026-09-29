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
      <div v-if="unpackArchive && archiveLoading" role="status">
        Loading ZIP archive...
      </div>
      <div
        v-if="unpackArchive && archiveError"
        class="alert alert-danger"
        role="alert"
      >
        {{ archiveError }}
      </div>
      <div v-if="unpackArchive && archiveFiles.length" class="archive-files">
        <p class="archive-count" aria-live="polite">
          {{ attachedFilesCount }} of {{ archiveFiles.length }} files will be
          attached
        </p>
        <div
          v-for="(file, index) in archiveFiles"
          :key="index"
          class="archive-card"
          :class="{ 'archive-card-excluded': file.doNotAttach }"
        >
          <div class="archive-card-header">
            <div class="archive-filename">
              <label class="sr-only" :for="`archive_basename_${index}`">
                File basename for {{ file.originalName }}
              </label>
              <input
                :id="`archive_basename_${index}`"
                v-model="file.basename"
                class="form-control archive-basename"
                type="text"
                :disabled="disabled"
                @input="emitArchive"
              />
              <span
                :id="`archive_extension_${index}`"
                class="archive-extension"
                :aria-label="`File extension: ${file.extension || 'none'}`"
              >
                {{ file.extension ? file.extension.toUpperCase() : "NO EXT" }}
              </span>
            </div>
            <label class="archive-skip" :for="`archive_skip_${index}`">
              <input
                :id="`archive_skip_${index}`"
                v-model="file.doNotAttach"
                type="checkbox"
                :disabled="disabled"
                @change="emitArchive"
              />
              Do not attach file
              <span class="sr-only">
                {{ index + 1 }}: {{ file.originalName }}
              </span>
            </label>
          </div>
          <details
            v-if="file.text !== null"
            class="archive-content"
            :open="index === firstTextIndex"
          >
            <summary>
              View/edit contents
              <span class="sr-only">
                of file {{ index + 1 }}: {{ file.originalName }}
              </span>
            </summary>
            <label class="sr-only" :for="`archive_content_${index}`">
              Content of {{ file.originalName }}
            </label>
            <textarea
              :id="`archive_content_${index}`"
              v-model="file.text"
              class="form-control archive-content-editor"
              rows="5"
              spellcheck="false"
              :disabled="disabled"
              @input="emitArchive"
            ></textarea>
          </details>
        </div>
      </div>
      <template v-if="!unpackArchive">
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
              :disabled="disabled"
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
              :disabled="disabled"
              :readonly="content === 'Content loading...'"
            ></textarea>
          </div>
        </div>
      </template>
    </div>
    <hr />
  </div>
</template>

<script>
import { computed, defineComponent, markRaw, onMounted, ref, watch } from "vue";
import * as api from "../../api";
import { errorParser } from "../../helpers";
import { loadTestcaseArchive } from "../../testcase_archive";

export default defineComponent({
  name: "TestCaseSection",

  props: {
    mode: {
      type: String,
      required: false,
      default: "bug",
    },
    disabled: {
      type: Boolean,
      default: false,
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

  emits: [
    "update-not-attach-test",
    "update-filename",
    "update-content",
    "update-archive",
  ],
  setup(props, { emit }) {
    const notAttachTest = ref(false);
    const unpackArchive = ref(false);
    const archiveLoading = ref(false);
    const archiveError = ref(null);
    const archiveFiles = ref([]);
    const attachedFilesCount = computed(
      () => archiveFiles.value.filter((file) => !file.doNotAttach).length,
    );
    const firstTextIndex = computed(() =>
      archiveFiles.value.findIndex((file) => file.text !== null),
    );
    const isZip = computed(() => /\.zip$/i.test(props.entry.testcase || ""));
    const filename = computed({
      get: () => props.fileName,
      set: (value) => emit("update-filename", value),
    });
    const content = ref("Content loading...");

    const emitArchive = () => {
      emit("update-archive", {
        enabled: unpackArchive.value,
        loading: archiveLoading.value,
        error: archiveError.value,
        files: archiveFiles.value,
      });
    };

    const onUnpackChange = async () => {
      if (!unpackArchive.value) {
        emitArchive();
        return;
      }
      if (archiveFiles.value.length) {
        emitArchive();
        return;
      }
      archiveLoading.value = true;
      archiveError.value = null;
      emitArchive();
      try {
        archiveFiles.value = (await loadTestcaseArchive(props.entry.id)).map(
          (file) => ({
            ...file,
            bytes: markRaw(file.bytes),
          }),
        );
      } catch (error) {
        archiveError.value = `Unable to unpack ZIP archive: ${errorParser(error)}`;
      } finally {
        archiveLoading.value = false;
        emitArchive();
      }
    };

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
      unpackArchive,
      archiveLoading,
      archiveError,
      archiveFiles,
      attachedFilesCount,
      firstTextIndex,
      isZip,
      onUnpackChange,
      emitArchive,
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

.archive-card {
  background: #fff;
  border: 1px solid #d8dee7;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  margin-bottom: 12px;
  padding: 14px 16px;
}

.archive-card-excluded {
  background: #f5f6f8;
  color: #667085;
}

.archive-card-header,
.archive-filename {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.archive-card-header {
  justify-content: space-between;
}

.archive-filename {
  flex: 1 1 360px;
  min-width: 0;
}

.archive-basename {
  flex: 0 1 280px;
  max-width: 280px;
  min-width: 160px;
}

.archive-extension {
  background: #e8efff;
  border-radius: 999px;
  color: #175cd3;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  white-space: nowrap;
}

.archive-card-excluded .archive-extension {
  background: #e2e5ea;
  color: #475467;
}

.archive-skip {
  cursor: pointer;
  font-weight: normal;
  margin: 0;
}

.archive-skip input {
  margin-right: 5px;
}

.archive-content {
  margin-top: 12px;
}

.archive-content summary {
  color: #175cd3;
  cursor: pointer;
  width: fit-content;
}

.archive-content-editor {
  font-family: monospace;
  margin-top: 12px;
  resize: vertical;
}
</style>
