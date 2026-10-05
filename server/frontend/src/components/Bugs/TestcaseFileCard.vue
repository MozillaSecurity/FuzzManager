<template>
  <div
    class="archive-card"
    :class="{ 'archive-card-excluded': file.doNotAttach }"
  >
    <div class="archive-card-header">
      <div class="archive-filename">
        <span v-if="file.doNotAttach" class="archive-excluded-name">
          {{ file.basename || file.originalName }}
        </span>
        <template v-else>
          <label class="sr-only" :for="ids.basename">
            File basename for {{ file.originalName }}
          </label>
          <input
            :id="ids.basename"
            :value="file.basename"
            class="form-control archive-basename"
            type="text"
            :disabled="disabled"
            @input="$emit('update:basename', $event.target.value)"
          />
        </template>
        <span
          :id="ids.extension"
          class="archive-extension"
          :aria-label="`File extension: ${file.extension || 'none'}`"
        >
          {{ file.extension ? file.extension.toUpperCase() : "NO EXT" }}
        </span>
      </div>
      <label v-if="!single" class="archive-skip" :for="ids.skip">
        <input
          :id="ids.skip"
          :checked="file.doNotAttach"
          type="checkbox"
          :disabled="disabled"
          @change="$emit('update:doNotAttach', $event.target.checked)"
        />
        Do not attach file
        <span class="sr-only"> {{ index + 1 }}: {{ file.originalName }} </span>
      </label>
    </div>
    <details
      v-if="!file.doNotAttach && file.text !== null"
      class="archive-content"
      open
    >
      <summary>
        View/edit contents
        <span class="sr-only">
          of file {{ index + 1 }}: {{ file.originalName }}
        </span>
      </summary>
      <label class="sr-only" :for="ids.content">
        Content of {{ file.originalName }}
      </label>
      <textarea
        :id="ids.content"
        :value="file.text"
        class="form-control archive-content-editor"
        rows="5"
        spellcheck="false"
        :disabled="disabled"
        @input="$emit('update:text', $event.target.value)"
      ></textarea>
    </details>
  </div>
</template>

<script>
import { computed, defineComponent } from "vue";

export default defineComponent({
  name: "TestcaseFileCard",
  props: {
    file: { type: Object, required: true },
    index: { type: Number, default: 0 },
    single: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  emits: ["update:basename", "update:text", "update:doNotAttach"],
  setup(props) {
    const ids = computed(() =>
      props.single
        ? {
            basename: "id_testcase_filename",
            extension: "file_extension",
            skip: "id_testcase_file_skip",
            content: "id_testcase_content",
          }
        : Object.fromEntries(
            ["basename", "extension", "skip", "content"].map((name) => [
              name,
              `archive_${name}_${props.index}`,
            ]),
          ),
    );
    return { ids };
  },
});
</script>

<style scoped>
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
  padding-bottom: 9px;
  padding-top: 9px;
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

.archive-excluded-name {
  overflow-wrap: anywhere;
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
