<template>
  <div class="panel panel-info">
    <div class="panel-heading">
      <i class="bi bi-tag-fill"></i>
      {{ bucketId ? "Edit Bucket" : "New Bucket" }}
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
        <a href="#reports_in">list</a>):
        <span class="badge">{{ inListCount }}</span>
      </p>
      <p v-if="outList.length">
        Issues that will be removed from this bucket (
        <a href="#reports_out">list</a>):
        <span class="badge">{{ outListCount }}</span>
      </p>

      <form v-on:submit.prevent="">
        <label for="id_description">Description</label><br />
        <input
          id="id_description"
          class="form-control"
          maxlength="1023"
          type="text"
          v-model="bucket.description"
        />
        <br />

        <label for="id_priority">Priority</label><br />
        <input
          id="id_priority"
          class="form-control"
          type="number"
          min="-2"
          max="2"
          v-model="bucket.priority"
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
          <input type="checkbox" id="id_reassign" v-model="reassign" />
          <label for="id_reassign">
            Reassign matching reports (reports in this bucket and lower-priority
            buckets will be reassigned)
          </label>
        </div>
        <div class="btn-group" v-if="bucketId">
          <button
            type="submit"
            class="btn btn-success"
            v-on:click="update(true)"
            :disabled="loading"
          >
            {{ loading === "save" ? "Saving..." : "Save" }}
          </button>
          <button
            type="submit"
            class="btn btn-default"
            v-on:click="update(false)"
            :disabled="loading"
          >
            {{ loading === "preview" ? "Loading preview..." : "Preview" }}
          </button>
        </div>
        <div class="btn-group" v-else>
          <button
            type="submit"
            class="btn btn-success"
            v-on:click="create(true)"
            :disabled="loading"
          >
            {{ loading === "create" ? "Creating..." : "Create" }}
          </button>
          <button
            type="submit"
            class="btn btn-default"
            v-on:click="create(false)"
            :disabled="loading"
          >
            {{ loading === "preview" ? "Loading preview..." : "Preview" }}
          </button>
        </div>
      </form>

      <div class="field">
        <template v-if="inList.length">
          <label id="reports_in">
            New issues that will be assigned to this bucket
            {{ inListCount > inList.length ? " (truncated)" : "" }}:
          </label>
          <List :entries="inList" />
        </template>

        <template v-if="outList.length">
          <label id="reports_out">
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
import List from "./ReportEntries/List.vue";

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
      description: "",
      priority: 0,
      signature: "",
    },
    reassign: true,
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
      this.bucket.description = this.proposedDescription;
    if (this.warningMessage) this.warning = this.warningMessage;
  },
  methods: {
    async create(save) {
      this.loading = save ? "create" : "preview";
      const payload = {
        description: this.bucket.description,
        priority: this.bucket.priority,
        signature: this.bucket.signature,
      };

      try {
        const data = await api.createBucket({
          params: { save: save, reassign: this.reassign },
          ...payload,
        });
        if (save) {
          window.location.href = data.url;
        }
        this.warning = data.warning_message;
        this.inList = data.in_list;
        this.outList = data.out_list;
        this.inListCount = data.in_list_count;
        this.outListCount = data.out_list_count;
      } catch (err) {
        this.warning = errorParser(err);
      } finally {
        this.loading = null;
      }
    },
    async update(save) {
      this.loading = save ? "save" : "preview";
      const payload = {
        description: this.bucket.description,
        priority: this.bucket.priority,
        signature: this.bucket.signature,
      };

      try {
        const data = await api.updateBucket({
          id: this.bucketId,
          params: { save: save, reassign: this.reassign },
          ...payload,
        });
        if (save) {
          window.location.href = data.url;
        }
        this.warning = data.warning_message;
        this.inList = data.in_list;
        this.outList = data.out_list;
        this.inListCount = data.in_list_count;
        this.outListCount = data.out_list_count;
      } catch (err) {
        this.warning = errorParser(err);
      } finally {
        this.loading = null;
      }
    },
  },
};
</script>

<style scoped></style>
