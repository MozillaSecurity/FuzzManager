<template>
  <div class="panel panel-info">
    <div class="panel-heading">
      <i class="bi bi-tag-fill"></i>
      {{ bucketId ? "Edit Signature" : "New Signature" }}
    </div>
    <div class="panel-body">
      <div class="alert alert-info" role="alert" v-if="loading === 'preview'">
        Loading preview...
      </div>
      <div class="alert alert-warning" role="alert" v-if="warning">
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

      <form v-on:submit.prevent="">
        <label for="id_shortDescription">Description</label><br />
        <input
          id="id_shortDescription"
          class="form-control"
          maxlength="1023"
          type="text"
          v-model="bucket.shortDescription"
        />
        <br />
        <label for="id_signature">Signature</label><br />
        <textarea
          id="id_signature"
          class="form-control"
          spellcheck="false"
          v-model="bucket.signature"
        ></textarea>

        <div class="field">
          <input type="checkbox" id="id_frequent" v-model="bucket.frequent" />
          <label for="id_frequent">Mark this bucket as a frequent bucket</label>
        </div>

        <div class="field">
          <input type="checkbox" id="id_permanent" v-model="bucket.permanent" />
          <label for="id_permanent">
            Mark this bucket as a permanent bucket
          </label>
        </div>

        <div class="field">
          <input
            type="checkbox"
            id="id_do_not_reduce"
            v-model="bucket.doNotReduce"
          />
          <label for="id_do_not_reduce">
            Mark this bucket &ldquo;do not reduce&rdquo;
          </label>
        </div>

        <div class="field">
          <input type="checkbox" id="id_reassign" v-model="reassign" />
          <label for="id_reassign">
            Reassign matching crashes (unassigned crashes and crashes assigned
            to this bucket will be reassigned)
          </label>
        </div>
        <div class="btn-group" v-if="bucketId">
          <button
            type="submit"
            class="btn btn-success"
            v-on:click="create_or_update(true)"
            :disabled="loading"
          >
            {{ loading === "save" ? "Saving..." : "Save" }}
          </button>
          <button
            type="submit"
            class="btn btn-default"
            v-on:click="create_or_update(false)"
            :disabled="loading"
          >
            {{ loading === "preview" ? "Loading preview..." : "Preview" }}
          </button>
        </div>
        <div class="btn-group" v-else>
          <button
            type="submit"
            class="btn btn-success"
            v-on:click="create_or_update(true)"
            :disabled="loading"
          >
            {{ loading === "create" ? "Creating..." : "Create" }}
          </button>
          <button
            type="submit"
            class="btn btn-default"
            v-on:click="create_or_update(false)"
            :disabled="loading"
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
import { errorParser } from "../../helpers";
import * as api from "../../api";
import List from "./CrashEntries/List.vue";

export default {
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
  data: () => ({
    bucket: {
      doNotReduce: false,
      frequent: false,
      permanent: false,
      shortDescription: "",
      signature: "",
    },
    reassign: true,
    reassignAsyncTimer: null,
    reassignAsyncToken: null,
    reassignDoneUrl: null,
    warning: "",
    inList: [],
    inListCount: 0,
    outList: [],
    outListCount: 0,
    loading: null,
  }),
  async mounted() {
    if (this.bucketId) this.bucket = await api.retrieveBucket(this.bucketId);
    if (this.proposedSignature)
      this.bucket.signature = JSON.stringify(this.proposedSignature, null, 2);
    if (this.proposedDescription)
      this.bucket.shortDescription = this.proposedDescription;
    if (this.warningMessage) this.warning = this.warningMessage;
  },
  methods: {
    async create_or_update(save) {
      this.warning = "";
      this.loading = save ? (this.bucketId ? "save" : "create") : "preview";
      const payload = {
        doNotReduce: this.bucket.doNotReduce,
        frequent: this.bucket.frequent,
        permanent: this.bucket.permanent,
        shortDescription: this.bucket.shortDescription,
        signature: this.bucket.signature,
      };

      try {
        const data = await (async () => {
          if (this.bucketId)
            return api.updateBucket({
              id: this.bucketId,
              params: { save: save, reassign: this.reassign },
              ...payload,
            });
          return api.createBucket({
            params: { save: save, reassign: this.reassign },
            ...payload,
          });
        })();
        if (save) {
          if (!this.reassign) {
            window.location.href = data.url;
          } else {
            // - start timer loop to poll token
            const { token, url } = data;
            this.reassignAsyncToken = token;
            this.reassignDoneUrl = url;
            this.reassignAsyncTimer = setTimeout(this.pollReassignDone, 1000);
          }
          return;
        }
        this.warning = data.warningMessage;
        this.inList = data.inList;
        this.outList = data.outList;
        this.inListCount = data.inListCount;
        this.outListCount = data.outListCount;
        this.loading = null;
      } catch (err) {
        this.warning = errorParser(err);
        this.loading = null;
      }
    },
    pollReassignDone: async function () {
      this.reassignAsyncTimer = null;
      let reassignDone;
      try {
        reassignDone = await api.pollAsyncOp(this.reassignAsyncToken);
      } catch (err) {
        // if the page loaded, but the fetch failed, either the network went away or we need to refresh auth
        // eslint-disable-next-line no-console
        console.debug(errorParser(err));
        window.location.href = this.reassignDoneUrl;
        return;
      }
      if (reassignDone) {
        this.reassignAsyncToken = null;
        window.location.href = this.reassignDoneUrl;
      } else {
        this.reassignAsyncTimer = setTimeout(this.pollReassignDone, 1000);
      }
    },
  },
};
</script>

<style scoped></style>
