<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-card-list"></i> Create an external comment
    </div>
    <div class="panel-body">
      <h3>Configuration</h3>
      <div class="row">
        <div class="form-group col-md-6">
          <label for="bp_select">Bug provider</label>
          <select
            id="bp_select"
            class="form-control"
            v-model="selectedProvider"
          >
            <option v-for="p in providers" :key="p.id" :value="p.id">
              {{ p.hostname }}
            </option>
          </select>
        </div>
        <div class="form-group col-md-6">
          <label for="bt_select">Comment template</label>
          <select
            id="bt_select"
            class="form-control"
            v-model="selectedTemplate"
          >
            <option v-for="t in templates" :key="t.id" :value="t.id">
              {{ t.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="alert alert-warning" role="alert" v-if="provider">
        You are about to submit this comment to
        <strong>{{ provider.hostname }}</strong>
      </div>
      <hr />

      <h3>Publish a comment on report {{ entryId }}</h3>
      <div class="alert alert-info" role="alert" v-if="!template">
        Please pick a comment template to file a new comment.
      </div>
      <form v-else>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="bug_id">Bug ID*</label>
            <input
              type="text"
              id="id_bugid"
              class="form-control"
              maxlength="255"
              name="bug_id"
              v-model="externalBugId"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="is_private">Flags</label>
            <br />
            <input
              type="checkbox"
              id="id_private"
              name="is_private"
              v-model="isPrivate"
            />
            <span>This is a private comment.</span>
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="comment">Comment</label>
            <HelpPopover
              field="comment"
              :variables="entryfields"
              documentation-link="https://github.com/MozillaSecurity/WebCompatManager/blob/master/doc/BugzillaVariables.md#in-comment-field"
            />
            <textarea
              id="id_comment"
              class="form-control"
              name="comment"
              v-model="template.comment"
            ></textarea>
          </div>
          <div class="form-group col-md-6">
            <label for="rendered_description">Rendered comment</label>
            <textarea
              id="id_rendered_comment"
              class="form-control"
              name="rendered_comment"
              readonly
              :value="renderedComment"
            >
            </textarea>
          </div>
        </div>
        <hr />

        <div v-if="createError" class="alert alert-danger" role="alert">
          <button
            type="button"
            class="close"
            data-dismiss="alert"
            aria-label="Close"
            v-on:click="createError = null"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          An error occurred while submitting the comment to
          <strong>{{ provider.hostname }}</strong
          >: {{ createError }}
        </div>

        <div
          v-else-if="createdCommentId"
          class="alert alert-success"
          role="alert"
        >
          Comment
          <strong>
            <a :href="commentLink" target="_blank">{{ createdCommentId }}</a>
          </strong>
          was successfully submitted and created on
          <strong>{{ provider.hostname }}</strong> provider.
        </div>

        <div v-if="!bugzillaToken" class="alert alert-warning" role="alert">
          Please define an API Token for
          <strong>{{ provider.hostname }}</strong> in your settings to submit a
          new comment.
        </div>

        <div>
          <button
            type="button"
            class="btn btn-danger"
            v-on:click="createExternalComment"
            :disabled="!bugzillaToken || submitting"
          >
            Submit
          </button>
          <button
            type="button"
            class="btn btn-default"
            v-on:click="goBack"
            :disabled="submitting"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import Handlebars from "handlebars";
import * as HandlebarsHelpers from "../../../handlebars_helpers";
import { errorParser } from "../../../helpers";
import * as api from "../../../api";
import * as bugzillaApi from "../../../bugzilla_api";
import HelpPopover from "../HelpPopover.vue";

// Apply Handlebars helpers
Object.entries(HandlebarsHelpers).forEach(([name, callback]) => {
  Handlebars.registerHelper(name, callback);
});

export default {
  components: {
    HelpPopover,
  },
  props: {
    providerId: {
      type: Number,
      required: true,
    },
    templateId: {
      type: Number,
      required: true,
    },
    entryId: {
      type: Number,
      required: true,
    },
    bugId: {
      type: Number,
      required: false,
      default: null,
    },
  },
  data: () => ({
    providers: [],
    selectedProvider: null,
    provider: null,
    templates: [],
    selectedTemplate: null,
    template: null,
    entry: null,
    externalBugId: "",
    isPrivate: false,
    submitting: false,
    summary: "",
    createError: null,
    createdCommentId: null,
    createdCommentCount: null,
    entryfields: [
      "summary",
      "app_name",
      "app_channel",
      "app_version",
      "breakage_category",
      "os",
      "url",
      "url_scheme",
      "url_netloc",
      "url_path",
      "url_query",
      "url_fragment",
      "url_username",
      "url_password",
      "url_hostname",
      "url_port",
      "uuid",
    ],
  }),
  async mounted() {
    this.entry = await api.retrieveReport(this.entryId);
    if (this.bugId) this.externalBugId = this.bugId;

    let data = await api.listBugProviders();
    this.providers = data.results.filter(
      (p) => p.classname === "BugzillaProvider",
    );
    this.provider = this.providers.find((p) => p.id === this.providerId);
    this.selectedProvider = this.provider.id;

    data = await api.listTemplates();
    this.templates = data.results.filter((t) => t.mode === "comment");
    this.template = this.templates.find((t) => t.id === this.templateId);
    if (this.template) {
      this.selectedTemplate = this.template.id;
    }
    this.summary = this.template.summary;
  },
  computed: {
    commentLink() {
      return `https://${this.provider.hostname}/show_bug.cgi?id=${this.externalBugId}#c${this.createdCommentCount}`;
    },
    bugzillaToken() {
      return localStorage.getItem("provider-" + this.provider.id + "-api-key");
    },
    entryMetadata() {
      if (this.entry && this.entry.metadata)
        return JSON.parse(this.entry.metadata);
      return {};
    },
    renderedComment() {
      if (!this.template || !this.entry) return "";
      try {
        const compiled = Handlebars.compile(this.template.comment);
        let rendered = compiled({
          summary: this.summary,
          ...this.entryExtension(),
        });

        return rendered;
      } catch {
        return "";
      }
    },
  },
  methods: {
    goBack() {
      window.history.back();
    },
    entryExtension() {
      const pts = new URL(this.entry.url);
      return {
        app_channel: this.entry.app_channel,
        app_name: this.entry.app_name,
        app_version: this.entry.app_version,
        breakage_category: this.entry.breakage_category,
        os: this.entry.os,
        url: this.entry.url,
        url_fragment: pts.hash,
        url_hostname: pts.hostname,
        url_netloc: pts.host,
        url_password: pts.password,
        url_path: pts.pathname,
        url_port: pts.port,
        url_query: pts.search,
        url_scheme: pts.protocol,
        url_username: pts.username,
        uuid: this.entry.uuid,
      };
    },
    async createExternalComment() {
      this.submitting = true;
      this.createdCommentId = null;
      this.createdCommentCount = null;
      this.createError = null;

      const payload = {
        id: this.externalBugId,
        comment: this.renderedComment,
        is_markdown: true,
        is_private: this.isPrivate,
      };

      try {
        let data = await bugzillaApi.createComment({
          hostname: this.provider.hostname,
          id: this.externalBugId,
          ...payload,
          headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
        });
        this.createdCommentId = data.id;

        // Retrieving comment info to publish attachments and forge comment link
        data = await bugzillaApi.retrieveComment({
          hostname: this.provider.hostname,
          id: this.createdCommentId,
          headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
        });
        this.createdCommentCount =
          data.comments && data.comments[this.createdCommentId]
            ? data.comments[this.createdCommentId].count
            : undefined;
      } catch (err) {
        this.createError = errorParser(err);
      } finally {
        this.submitting = false;
      }
    },
  },
  watch: {
    selectedProvider() {
      this.provider = this.providers.find(
        (p) => p.id === this.selectedProvider,
      );
    },
    selectedTemplate() {
      this.template = this.templates.find(
        (t) => t.id === this.selectedTemplate,
      );
    },
  },
};
</script>

<style scoped></style>
