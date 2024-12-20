<template>
  <div class="panel panel-info">
    <div class="panel-heading">
      <i class="bi bi-tag-fill"></i>
      {{ bucketId ? "Edit Signature" : "New Signature" }}
    </div>
    <div class="panel-body">
      <div v-if="loading === 'preview'" class="alert alert-info" role="alert">
        Loading preview...
      </div>
      <div v-if="warning" class="alert alert-warning" role="alert">
        {{ warning }}
      </div>

      <p v-if="inList.length">
        New issues that will be assigned to this bucket (
        <a href="#crashes_in">list</a>):
        <span class="badge">{{ inListCount }}</span>
      </p>
      <p v-if="outList.length">
        Issues that will be removed from this bucket (
        <a href="#crashes_out">list</a>):
        <span class="badge">{{ outListCount }}</span>
      </p>

      <form @submit.prevent="">
        <label for="id_shortDescription">Description</label><br />
        <input
          id="id_shortDescription"
          v-model="bucket.shortDescription"
          class="form-control"
          maxlength="1023"
          type="text"
        />
        <br />
        <label for="id_signature">Signature</label><br />
        <textarea
          id="id_signature"
          v-model="bucket.signature"
          class="form-control"
          spellcheck="false"
        ></textarea>

        <div class="field">
          <input id="id_frequent" v-model="bucket.frequent" type="checkbox" />
          <label for="id_frequent">Mark this bucket as a frequent bucket</label>
        </div>

        <div class="field">
          <input id="id_permanent" v-model="bucket.permanent" type="checkbox" />
          <label for="id_permanent">
            Mark this bucket as a permanent bucket
          </label>
        </div>

        <div class="field">
          <input
            id="id_do_not_reduce"
            v-model="bucket.doNotReduce"
            type="checkbox"
          />
          <label for="id_do_not_reduce">
            Mark this bucket &ldquo;do not reduce&rdquo;
          </label>
        </div>

        <div class="field">
          <input id="id_reassign" v-model="reassign" type="checkbox" />
          <label for="id_reassign">
            Reassign matching crashes (unassigned crashes and crashes assigned
            to this bucket will be reassigned)
          </label>
        </div>
        <div v-if="bucketId" class="btn-group">
          <button
            type="submit"
            class="btn btn-success"
            :disabled="loading"
            @click="create_or_update(true)"
          >
            {{ loading === "save" ? "Saving..." : "Save" }}
          </button>
          <button
            type="submit"
            class="btn btn-default"
            :disabled="loading"
            @click="create_or_update(false)"
          >
            {{ loading === "preview" ? "Loading preview..." : "Preview" }}
          </button>
        </div>
        <div v-else class="btn-group">
          <button
            type="submit"
            class="btn btn-success"
            :disabled="loading"
            @click="create_or_update(true)"
          >
            {{ loading === "create" ? "Creating..." : "Create" }}
          </button>
          <button
            type="submit"
            class="btn btn-default"
            :disabled="loading"
            @click="create_or_update(false)"
          >
            {{ loading === "preview" ? "Loading preview..." : "Preview" }}
          </button>
        </div>
      </form>

      <div class="field">
        <template v-if="inList.length">
          <label id="crashes_in">
            New issues that will be assigned to this bucket
            {{ inListCount > inList.length ? " (truncated)" : "" }}:
          </label>
          <List :entries="inList" />
        </template>

        <template v-if="outList.length">
          <label id="crashes_out">
            Issues that will be removed from this bucket
            {{ outListCount > outList.length ? " (truncated)" : "" }}:
          </label>
          <List :entries="outList" />
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, onMounted, ref } from "vue";
import * as api from "../../api";
import { errorParser } from "../../helpers";
import List from "./CrashEntries/List.vue";

export default defineComponent({
  components: {
    List,
  },
  props: {
    bucketId: {
      type: Number,
      default: null,
    },
    proposedSignature: {
      type: Object,
      default: null,
    },
    proposedDescription: {
      type: String,
      default: null,
    },
    warningMessage: {
      type: String,
      default: null,
    },
  },
  setup(props) {
    const bucket = ref({
      doNotReduce: false,
      frequent: false,
      permanent: false,
      shortDescription: "",
      signature: "",
    });
    const reassign = ref(true);
    const warning = ref("");
    const inList = ref([]);
    const inListCount = ref(0);
    const outList = ref([]);
    const outListCount = ref(0);
    const loading = ref(null);

    onMounted(async () => {
      if (props.bucketId) {
        bucket.value = await api.retrieveBucket(props.bucketId);
      }
      if (props.proposedSignature) {
        bucket.value.signature = JSON.stringify(
          props.proposedSignature,
          null,
          2,
        );
      }
      if (props.proposedDescription) {
        bucket.value.shortDescription = props.proposedDescription;
      }
      if (props.warningMessage) {
        warning.value = props.warningMessage;
      }
    });

    const create_or_update = async (save) => {
      warning.value = "";
      loading.value = save ? (props.bucketId ? "save" : "create") : "preview";

      const payload = {
        doNotReduce: bucket.value.doNotReduce,
        frequent: bucket.value.frequent,
        permanent: bucket.value.permanent,
        shortDescription: bucket.value.shortDescription,
        signature: bucket.value.signature,
      };

      try {
        let offset = 0;
        let bucket_id;

        while (offset !== null) {
          const data = await (async () => {
            if (props.bucketId || bucket_id) {
              return api.updateBucket({
                id: props.bucketId || bucket_id,
                params: { save, reassign: reassign.value, offset },
                ...payload,
              });
            }
            return api.createBucket({
              params: { save, reassign: reassign.value, offset },
              ...payload,
            });
          })();

          if (data.bucket_id) bucket_id = data.bucket_id;

          if (data.url) {
            window.location.href = data.url;
            return;
          }

          warning.value = data.warningMessage;
          if (offset === 0) {
            inList.value = data.inList;
            outList.value = data.outList;
            inListCount.value = data.inListCount;
            outListCount.value = data.outListCount;
          } else {
            inList.value.push(...data.inList);
            outList.value.push(...data.outList);
            inListCount.value += data.inListCount;
            outListCount.value += data.outListCount;
          }
          offset = data.nextOffset;
        }
        loading.value = null;
      } catch (err) {
        warning.value = errorParser(err);
        loading.value = null;
      }
    };

    return {
      bucket,
      reassign,
      warning,
      inList,
      inListCount,
      outList,
      outListCount,
      loading,
      create_or_update,
    };
  },
});
</script>

<style scoped></style>
