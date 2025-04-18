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
            v-model="selectedProvider"
            class="form-control"
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
            v-model="selectedTemplate"
            class="form-control"
          >
            <option v-for="t in templates" :key="t.id" :value="t.id">
              {{ t.name }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="provider" class="alert alert-warning" role="alert">
        You are about to submit this comment to
        <strong>{{ provider.hostname }}</strong>
      </div>
      <hr />

      <h3>Publish a comment on crash {{ entryId }}</h3>
      <div v-if="!template" class="alert alert-info" role="alert">
        Please pick a comment template to file a new comment.
      </div>
      <form v-else>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="bug_id">Bug ID*</label>
            <input
              id="id_bugid"
              v-model="externalBugId"
              type="text"
              class="form-control"
              maxlength="255"
              name="bug_id"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="is_private">Flags</label>
            <br />
            <input
              id="id_private"
              v-model="isPrivate"
              type="checkbox"
              name="is_private"
            />
            <span>This is a private comment.</span>
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="comment">Comment</label>
            <HelpPopover
              field="comment"
              :variables="[
                'summary',
                'shortsig',
                'product',
                'version',
                'args',
                'os',
                'platform',
                'client',
                'testcase',
                'crashdata',
                'crashdataattached',
                'metadata*',
              ]"
              documentation-link="https://github.com/MozillaSecurity/FuzzManager/blob/master/doc/BugzillaVariables.md#in-comment-field"
            />
            <textarea
              id="id_comment"
              v-model="template.comment"
              class="form-control"
              name="comment"
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

        <CrashDataSection
          mode="comment"
          :initial-not-attach-data="notAttachData"
          :initial-data="crashData"
          :path-prefix="entryMetadata.pathprefix"
          @update-not-attach-data="notAttachData = $event"
          @update-data="crashData = $event"
        />

        <TestCaseSection
          v-if="entry.testcase"
          mode="comment"
          :initial-not-attach-test="notAttachTest"
          :entry="entry"
          :template="template"
          :file-extension="fileExtension"
          :file-name="fileName"
          @update-not-attach-test="notAttachTest = $event"
          @update-filename="newFileName = $event"
          @update-content="testCaseContent = $event"
        />

        <div v-if="createError" class="alert alert-danger" role="alert">
          <button
            type="button"
            class="close"
            data-dismiss="alert"
            aria-label="Close"
            @click="createError = null"
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

        <div
          v-if="publishCrashDataError"
          class="alert alert-danger"
          role="alert"
        >
          <button
            type="button"
            class="close"
            data-dismiss="alert"
            aria-label="Close"
            @click="publishCrashDataError = null"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          An error occurred while attaching crash data to the created external
          comment:
          {{ publishCrashDataError }}
        </div>

        <div
          v-if="publishTestCaseError"
          class="alert alert-danger"
          role="alert"
        >
          <button
            type="button"
            class="close"
            data-dismiss="alert"
            aria-label="Close"
            @click="publishTestCaseError = null"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          An error occurred while attaching the testcase to the created external
          comment:
          {{ publishTestCaseError }}
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
            :disabled="!bugzillaToken || submitting"
            @click="createExternalComment"
          >
            Submit
          </button>
          <button
            type="button"
            class="btn btn-default"
            :disabled="submitting"
            @click="goBack"
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
import { Base64 } from "js-base64";
import _orderBy from "lodash/orderBy";
import mime from "mime";
import { defineComponent } from "vue";
import * as api from "../../../api";
import * as bugzillaApi from "../../../bugzilla_api";
import * as HandlebarsHelpers from "../../../handlebars_helpers";
import { errorParser } from "../../../helpers";
import CrashDataSection from "../CrashDataSection.vue";
import HelpPopover from "../HelpPopover.vue";
import TestCaseSection from "../TestCaseSection.vue";

// Apply Handlebars helpers
Object.entries(HandlebarsHelpers).forEach(([name, callback]) => {
  Handlebars.registerHelper(name, callback);
});

export default defineComponent({
  name: "PublicationForm",
  components: {
    CrashDataSection,
    TestCaseSection,
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

  data() {
    return {
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
      createError: null,
      publishTestCaseError: null,
      publishCrashDataError: null,
      createdCommentId: null,
      createdCommentCount: null,
      notAttachTest: false,
      testCaseContent: "",
      notAttachData: false,
      crashData: "",
      newFileName: null,
    };
  },

  computed: {
    commentLink() {
      return `https://${this.provider.hostname}/show_bug.cgi?id=${this.externalBugId}#c${this.createdCommentCount}`;
    },

    bugzillaToken() {
      return localStorage.getItem("provider-" + this.provider.id + "-api-key");
    },

    entryMetadata() {
      if (this.entry?.metadata) return JSON.parse(this.entry.metadata);
      return {};
    },

    preSummary() {
      if (this.template?.summary) return this.template.summary;
      if (this.entry?.shortSignature?.startsWith("[@"))
        return "Crash " + this.entry.shortSignature;
      return this.entry?.shortSignature;
    },

    summary() {
      let s = this.preSummary;
      // Remove the specified pathPrefix from traces and assertion
      if (this.entryMetadata.pathprefix) {
        s = s.replaceAll(this.entryMetadata.pathprefix, "");
      }
      return s;
    },

    crashDataRendered() {
      return this.crashData
        .split("\n")
        .map((l) => "    " + l)
        .join("\n");
    },

    testCaseRendered() {
      if (!this.entry?.testcase) return "(Test not available)";
      else if (this.testCaseContent.length > 2048) return "See attachment.";
      return this.testCaseContent
        .split("\n")
        .map((l) => "    " + l)
        .join("\n");
    },

    renderedComment() {
      if (!this.template || !this.entry) return "";
      try {
        const compiled = Handlebars.compile(this.template.comment);
        const renderedData = {
          summary: this.summary,
          shortsig: this.entry.shortSignature,
          product: this.entry.product,
          version: this.entry.product_version
            ? this.entry.product_version
            : "(Version not available)",
          args: this.entry.args ? JSON.parse(this.entry.args).join(" ") : "",
          os: this.entry.os,
          platform: this.entry.platform,
          client: this.entry.client,
          testcase: this.testCaseRendered,
          crashdata: this.crashDataRendered,
          crashdataattached: this.notAttachData
            ? "(Crash data not available)"
            : "For detailed crash information, see attachment.",
          ...this.metadataExtension(this.template.comment),
        };

        if (!this.notAttachTest) {
          renderedData["testcase_attachment"] = this.filenameWithExtension;
        } else {
          delete renderedData["testcase_attachment"];
        }

        let rendered = compiled(renderedData);

        // Remove the specified pathPrefix from traces and assertion
        if (this.entryMetadata.pathprefix) {
          rendered = rendered.replaceAll(this.entryMetadata.pathprefix, "");
        }

        return rendered;
      } catch {
        return "";
      }
    },
    fileName() {
      const { attachmentFilename } = this.getFileDetails();

      return this.newFileName ?? attachmentFilename;
    },
    fileExtension() {
      const { attachmentFilenameExtension } = this.getFileDetails();

      return attachmentFilenameExtension;
    },
    filenameWithExtension() {
      return this.fileName + "." + this.fileExtension;
    },
    fileMimetype() {
      const mimeType = mime.getType(this.filenameWithExtension);

      if (mimeType) {
        return mimeType;
      }

      if (this.entry.testcase_isbinary) {
        return "application/octet-stream";
      }

      return "text/plain";
    },
  },

  watch: {
    selectedProvider(newVal) {
      this.provider = this.providers.find((p) => p.id === newVal);
    },
    selectedTemplate(newVal) {
      this.template = this.templates.find((t) => t.id === newVal);
    },
  },

  async mounted() {
    this.entry = await api.retrieveCrash(this.entryId);
    this.crashData = this.entry.rawCrashData
      ? this.entry.rawCrashData
      : this.entry.rawStderr;
    if (this.bugId) this.externalBugId = this.bugId;

    let data = await api.listBugProviders();
    this.providers = data.results.filter(
      (p) => p.classname === "BugzillaProvider",
    );
    this.provider = this.providers.find((p) => p.id === this.providerId);
    this.selectedProvider = this.provider.id;

    data = await api.listTemplates();
    this.templates = _orderBy(
      data.results.filter((t) => t.mode === "comment"),
      ["name"],
    );
    this.template = this.templates.find((t) => t.id === this.templateId);
    if (this.template) {
      this.selectedTemplate = this.template.id;
    }
  },

  methods: {
    goBack() {
      window.history.back();
    },

    metadataExtension(field) {
      let extension = {};
      for (const [key, value] of Object.entries(this.entryMetadata)) {
        extension["metadata" + key] = value;
      }
      if (field) {
        const regexp = new RegExp(/metadata([a-zA-Z0-9_-]+)/, "g");
        const matches = field.matchAll(regexp);
        for (const [match] of matches) {
          if (extension[match] === undefined)
            extension[match] = "(" + match + " not available)";
        }
      }
      return extension;
    },

    async createExternalComment() {
      this.submitting = true;
      this.createdCommentId = null;
      this.createdCommentCount = null;
      this.createError = null;
      this.publishTestCaseError = null;
      this.publishCrashDataError = null;

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
          data.comments?.[this.createdCommentId]?.count;

        await this.publishAttachments();
      } catch (err) {
        this.createError = errorParser(err);
      } finally {
        this.submitting = false;
      }
    },

    async publishAttachments() {
      if (!this.notAttachData) {
        const payload = {
          ids: [this.externalBugId],
          data: Base64.encode(this.crashData),
          file_name: "crash_data.txt",
          summary: "Detailed Crash Information",
          content_type: "text/plain",
        };

        try {
          await bugzillaApi.createAttachment({
            hostname: this.provider.hostname,
            id: this.externalBugId,
            ...payload,
            headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
          });
        } catch (err) {
          this.publishCrashDataError = errorParser(err);
        }
      }

      // Publish TestCase
      if (this.entry?.testcase && !this.notAttachTest) {
        let content = this.testCaseContent;
        // If the testcase is binary we need to download it first
        if (this.entry.testcase_isbinary) {
          content = await api.retrieveCrashTestCaseBinary(this.entry.id);
        }

        /*
         * A bug in BMO is causing "count" to be missing.
         * This workaround ensures we can still attach the missing file.
         */
        let comment = "previous comment";
        if (this.createdCommentCount !== undefined) {
          comment = `comment ${this.createdCommentCount}`;
        }

        const payload = {
          ids: [this.externalBugId],
          data: this.entry.testcase_isbinary
            ? Base64.fromUint8Array(content)
            : Base64.encode(content),
          file_name: this.filenameWithExtension,
          summary: `Testcase for ${comment}`,
          content_type: this.fileMimetype,
        };

        try {
          await bugzillaApi.createAttachment({
            hostname: this.provider.hostname,
            id: this.externalBugId,
            ...payload,
            headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
          });
        } catch (err) {
          this.publishTestCaseError = errorParser(err);
        }
      }
    },

    getFileDetails() {
      let attachmentFilename = "";
      let attachmentFilenameExtension = "";
      if (this.entry) {
        // extract file name
        const splittedAttachmentFilename = this.template?.testcase_filename
          ? this.template.testcase_filename
          : this.entry.testcase.split("/");

        const attachmentFilenameAndExtension =
          splittedAttachmentFilename[
            splittedAttachmentFilename?.length - 1
          ].split(".");

        attachmentFilename = attachmentFilenameAndExtension[0];
        attachmentFilenameExtension = attachmentFilenameAndExtension[1];
      }

      return { attachmentFilename, attachmentFilenameExtension };
    },
  },
});
</script>

<style scoped></style>
