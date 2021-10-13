<template>
  <div class="panel panel-default">
    <div class="panel-heading">
      <i class="bi bi-card-list"></i> Create an external bug
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
          <label for="bt_select">Bug template</label>
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
        You are about to submit this bug to
        <strong>{{ provider.hostname }}</strong>
      </div>
      <hr />

      <h3>Create a bug for crash {{ entryId }}</h3>
      <div class="alert alert-info" role="alert" v-if="!template">
        Please pick a bug template to file a new bug.
      </div>
      <form v-else>
        <SummaryInput
          v-if="provider"
          :initial-summary="summary"
          v-on:update-summary="summary = $event"
          :bucket-id="bucketId"
          :provider="provider"
        />

        <div class="row">
          <ProductComponentSelect
            v-if="provider"
            :provider-hostname="provider.hostname"
            :template-product="template.product"
            v-on:update-product="product = $event"
            :template-component="template.component"
            v-on:update-component="component = $event"
          />
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="whiteboard">Whiteboard</label>
            <input
              id="id_whiteboard"
              class="form-control"
              maxlength="1023"
              name="whiteboard"
              type="text"
              v-model="template.whiteboard"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="keywords">Keywords</label>
            <input
              id="id_keywords"
              class="form-control"
              maxlength="1023"
              name="keywords"
              type="text"
              v-model="template.keywords"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="op_sys">OS</label>
            <input
              id="id_op_sys"
              class="form-control"
              maxlength="1023"
              name="op_sys"
              type="text"
              v-model="opSys"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="platform">Platform</label>
            <input
              id="id_platform"
              class="form-control"
              maxlength="1023"
              name="platform"
              type="text"
              v-model="platform"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="cc">Cc</label>
            <UserDropdown
              v-if="provider && bugzillaToken"
              input-id="id_cc"
              input-name="cc"
              :provider="provider"
              :bugzilla-token="bugzillaToken"
              :initial-value="template.cc"
              :multiple="true"
              v-on:update-value="template.cc = $event"
            />
            <input
              v-else
              id="id_cc"
              class="form-control"
              maxlength="1023"
              name="cc"
              type="text"
              v-model="template.cc"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="assigned_to">Assigned to</label>
            <UserDropdown
              v-if="provider && bugzillaToken"
              input-id="id_assigned_to"
              input-name="assigned_to"
              :provider="provider"
              :bugzilla-token="bugzillaToken"
              :initial-value="template.assigned_to"
              v-on:update-value="template.assigned_to = $event"
            />
            <input
              v-else
              id="id_assigned_to"
              class="form-control"
              maxlength="1023"
              name="assigned_to"
              type="text"
              v-model="template.assigned_to"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="priority">Priority</label>
            <input
              id="id_priority"
              class="form-control"
              maxlength="1023"
              name="priority"
              type="text"
              v-model="template.priority"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="severity">Severity</label>
            <input
              id="id_severity"
              class="form-control"
              maxlength="1023"
              name="severity"
              type="text"
              v-model="template.severity"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="alias">Alias</label>
            <input
              id="id_alias"
              class="form-control"
              maxlength="1023"
              name="alias"
              type="text"
              v-model="template.alias"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="qa_contact">QA</label>
            <UserDropdown
              v-if="provider && bugzillaToken"
              input-id="id_qa_contact"
              input-name="qa_contact"
              :provider="provider"
              :bugzilla-token="bugzillaToken"
              :initial-value="template.qa_contact"
              v-on:update-value="template.qa_contact = $event"
            />
            <input
              v-else
              id="id_qa_contact"
              class="form-control"
              maxlength="1023"
              name="qa_contact"
              type="text"
              v-model="template.qa_contact"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="status">Status</label>
            <input
              id="id_status"
              class="form-control"
              maxlength="1023"
              name="status"
              type="text"
              v-model="template.status"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="resolution">Resolution</label>
            <input
              id="id_resolution"
              class="form-control"
              maxlength="1023"
              name="resolution"
              type="text"
              v-model="template.resolution"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="version">Version</label>
            <input
              id="id_version"
              class="form-control"
              maxlength="1023"
              name="version"
              type="text"
              v-model="template.version"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="target_milestone">Target milestone</label>
            <input
              id="id_target_milestone"
              class="form-control"
              maxlength="1023"
              name="target_milestone"
              type="text"
              v-model="template.target_milestone"
            />
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="dependson">Depends On</label>
            <input
              id="id_dependson"
              class="form-control"
              maxlength="1023"
              name="dependson"
              type="text"
              v-model="template.dependson"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="blocks">Blocks</label>
            <input
              id="id_blocks"
              class="form-control"
              maxlength="1023"
              name="blocks"
              type="text"
              v-model="template.blocks"
            />
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="attrs">Custom fields</label>
            <HelpPopover
              field="custom-fields"
              :variables="['metadata*']"
              documentation-link="https://github.com/MozillaSecurity/FuzzManager/blob/master/doc/BugzillaVariables.md#in-custom-fields-field"
            />
            <textarea
              id="id_attrs"
              class="form-control"
              name="attrs"
              v-model="template.attrs"
            ></textarea>
          </div>
          <div class="form-group col-md-6">
            <label for="attrs">Rendered custom fields</label>
            <textarea
              id="id_rendered_attrs"
              class="form-control"
              name="rendered_attrs"
              readonly
              :value="renderedAttrs"
            ></textarea>
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="description">Bug description</label>
            <HelpPopover
              field="description"
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
              documentation-link="https://github.com/MozillaSecurity/FuzzManager/blob/master/doc/BugzillaVariables.md#in-description-field"
            />
            <textarea
              id="id_description"
              class="form-control"
              name="description"
              v-model="template.description"
            ></textarea>
          </div>
          <div class="form-group col-md-6">
            <label for="rendered_description">Rendered description</label>
            <textarea
              id="id_rendered_description"
              class="form-control"
              name="rendered_description"
              readonly
              :value="renderedDescription"
            >
            </textarea>
          </div>
        </div>
        <hr />

        <h3>Security</h3>
        <div class="row">
          <div class="form-group col-md-6">
            <input
              type="checkbox"
              id="id_security"
              name="security"
              v-model="template.security"
            />
            <span>This is a security bug.</span>
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="security_group">
              Security Group (default is core-security)
            </label>
            <input
              type="text"
              class="form-control"
              maxlength="1023"
              id="id_security_group"
              name="security_group"
              v-model="template.security_group"
              :disabled="!template.security"
            />
          </div>
        </div>
        <hr />

        <CrashDataSection
          :initial-not-attach-data="notAttachData"
          v-on:update-not-attach-data="notAttachData = $event"
          :initial-data="crashData"
          v-on:update-data="crashData = $event"
          :path-prefix="entryMetadata.pathprefix"
        />

        <TestCaseSection
          v-if="entry.testcase"
          :initial-not-attach-test="notAttachTest"
          v-on:update-not-attach-test="notAttachTest = $event"
          :entry="entry"
          :template="template"
          v-on:update-filename="entry.testcase = $event"
          v-on:update-content="testCaseContent = $event"
        />

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
          An error occurred while submitting the bug to
          <strong>{{ provider.hostname }}</strong
          >: {{ createError }}
        </div>

        <div v-else-if="createdBugId" class="alert alert-success" role="alert">
          Bug
          <strong
            ><a :href="bugLink" target="_blank">{{ createdBugId }}</a></strong
          >
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
            v-on:click="publishCrashDataError = null"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          An error occurred while attaching crash data to the created external
          bug: {{ publishCrashDataError }}
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
            v-on:click="publishTestCaseError = null"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          An error occurred while attaching the testcase to the created external
          bug: {{ publishTestCaseError }}
        </div>

        <div v-if="assignError" class="alert alert-danger" role="alert">
          <button
            type="button"
            class="close"
            data-dismiss="alert"
            aria-label="Close"
            v-on:click="assignError = null"
          >
            <span aria-hidden="true">&times;</span>
          </button>
          An error occurred while assigning the created external bug to the
          current crash bucket: {{ assignError }}
        </div>

        <div v-if="!bugzillaToken" class="alert alert-warning" role="alert">
          Please define an API Token for
          <strong>{{ provider.hostname }}</strong> in your settings to submit a
          new bug.
        </div>

        <div>
          <button
            type="button"
            class="btn btn-danger"
            v-on:click="createExternalBug"
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
import * as HandlebarsHelpers from "../../handlebars_helpers";
import { Base64 } from "js-base64";
import { errorParser } from "../../helpers";
import * as api from "../../api";
import * as bugzillaApi from "../../bugzilla_api";
import SummaryInput from "./SummaryInput.vue";
import ProductComponentSelect from "./ProductComponentSelect.vue";
import UserDropdown from "./UserDropdown.vue";
import CrashDataSection from "./CrashDataSection.vue";
import TestCaseSection from "./TestCaseSection.vue";
import HelpPopover from "./HelpPopover.vue";

// Apply Handlebars helpers
Object.entries(HandlebarsHelpers).forEach(([name, callback]) => {
  Handlebars.registerHelper(name, callback);
});

export default {
  components: {
    SummaryInput,
    ProductComponentSelect,
    UserDropdown,
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
    bucketId: {
      type: Number,
      required: true,
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
    summary: "",
    product: "",
    component: "",
    opSys: "",
    platform: "",
    submitting: false,
    createError: null,
    publishTestCaseError: null,
    publishCrashDataError: null,
    assignError: null,
    createdBugId: null,
    notAttachTest: false,
    testCaseContent: "",
    notAttachData: false,
    crashData: "",
  }),
  async mounted() {
    this.entry = await api.retrieveCrash(this.entryId);
    this.crashData = this.entry.rawCrashData
      ? this.entry.rawCrashData
      : this.entry.rawStderr;

    let data = await api.listBugProviders();
    this.providers = data.results.filter(
      (p) => p.classname === "BugzillaProvider"
    );
    this.provider = this.providers.find((p) => p.id === this.providerId);
    this.selectedProvider = this.provider.id;

    data = await api.listTemplates();
    this.templates = data.results.filter((t) => t.mode === "bug");
    this.template = this.templates.find((t) => t.id === this.templateId);
    if (this.template) {
      this.selectedTemplate = this.template.id;
      this.updateFields();
    }
  },
  computed: {
    bugLink() {
      return `https://${this.provider.hostname}/${this.createdBugId}`;
    },
    bugzillaToken() {
      return localStorage.getItem("provider-" + this.provider.id + "-api-key");
    },
    entryMetadata() {
      if (this.entry && this.entry.metadata)
        return JSON.parse(this.entry.metadata);
      return {};
    },
    preSummary() {
      if (this.template.summary) return this.template.summary;
      if (
        this.entry.shortSignature &&
        this.entry.shortSignature.startsWith("[@")
      )
        return "Crash " + this.entry.shortSignature;
      return this.entry.shortSignature;
    },
    crashDataRendered() {
      return this.crashData
        .split("\n")
        .map((l) => "    " + l)
        .join("\n");
    },
    testCaseRendered() {
      if (!this.entry.testcase) return "(Test not available)";
      else if (this.testCaseContent.length > 2048) return "See attachment.";
      return this.testCaseContent
        .split("\n")
        .map((l) => "    " + l)
        .join("\n");
    },
    renderedAttrs() {
      if (!this.template || !this.entry) return "";
      try {
        const compiled = Handlebars.compile(this.template.attrs);
        let rendered = compiled({
          ...this.metadataExtension(this.template.attrs),
        });
        if (
          this.entry.shortSignature &&
          this.entry.shortSignature.startsWith("[@")
        )
          rendered += "\ncf_crash_signature=" + this.entry.shortSignature;
        return rendered;
      } catch {
        return "";
      }
    },
    renderedDescription() {
      if (!this.template || !this.entry) return "";
      try {
        const compiled = Handlebars.compile(this.template.description);
        let rendered = compiled({
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
          ...this.metadataExtension(this.template.description),
        });

        // Remove the specified pathPrefix from traces and assertion
        if (this.entryMetadata.pathprefix)
          rendered = rendered.replaceAll(this.entryMetadata.pathprefix, "");

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
    metadataExtension(field) {
      let extension = {};
      for (var [key, value] of Object.entries(this.entryMetadata)) {
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
    updateFields() {
      // Summary
      if (!this.entryMetadata.pathprefix) this.summary = this.preSummary;
      // Remove the specified pathPrefix from traces and assertion
      else
        this.summary = this.preSummary.replaceAll(
          this.entryMetadata.pathprefix,
          ""
        );

      // OpSys
      this.opSys = this.template.op_sys;
      if (!this.template.op_sys) {
        // Try to match the supplied os with the Bugzilla equivalent
        const os = this.entry.os.toLowerCase();
        if (os === "linux") this.opSys = "Linux";
        else if (os === "macosx") this.opSys = "macOS";
        else if (os === "windows") this.opSys = "Windows";
        else if (os === "android") this.opSys = "Android";
      }

      // Platform
      if (this.template.platform) this.platform = this.template.platform;
      // BMO uses x86_64, not x86-64, and ARM instead of arm
      else
        this.platform = this.entry.platform
          .replaceAll("-", "_")
          .replaceAll("arm", "ARM");
    },
    async createExternalBug() {
      this.submitting = true;
      this.createdBugId = null;
      this.createError = null;
      this.publishTestCaseError = null;
      this.publishCrashDataError = null;
      this.assignError = null;

      // Convert this.renderedAttrs to an object
      const attrs = Object.fromEntries(
        this.renderedAttrs.split("\n").map((l) => l.split("="))
      );

      let groups = [];
      if (this.template.security)
        groups = this.template.security_group
          ? [this.template.security_group]
          : ["core-security"];

      // Status ?? Resolution ??
      const rawPayload = {
        type: "defect",
        product: this.product,
        component: this.component,
        summary: this.summary,
        version: this.template.version,
        description: this.renderedDescription,
        op_sys: this.opSys,
        platform: this.platform,
        priority: this.template.priority,
        severity: this.template.severity,
        alias: this.template.alias,
        cc: this.template.cc.split(","),
        assigned_to: this.template.assigned_to,
        qa_contact: this.template.qa_contact,
        target_milestone: this.template.target_milestone,
        whiteboard: this.template.whiteboard,
        keywords: this.template.keywords,
        groups: groups.length ? groups : "",
        blocks: this.template.blocks.split(","),
        dependson: this.template.dependson.split(","),
        ...attrs,
      };

      const cleanPayload = {};
      Object.keys(rawPayload).forEach((prop) => {
        if (![null, undefined, NaN, ""].includes(rawPayload[prop])) {
          cleanPayload[prop] = rawPayload[prop];
        }
      });

      try {
        const data = await bugzillaApi.createBug({
          hostname: this.provider.hostname,
          ...cleanPayload,
          headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
        });
        this.createdBugId = data.id;
        await this.assignExternalBug();
        await this.publishAttachments();
      } catch (err) {
        this.createError = errorParser(err);
      } finally {
        this.submitting = false;
      }
    },
    async publishAttachments() {
      let payload = {};
      // Publish Crash data
      if (!this.notAttachData) {
        try {
          payload = {
            ids: [this.createdBugId],
            data: Base64.encode(this.crashData),
            file_name: "crash_data.txt",
            summary: "Detailed Crash Information",
            content_type: "text/plain",
          };

          await bugzillaApi.createAttachment({
            hostname: this.provider.hostname,
            id: this.createdBugId,
            ...payload,
            headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
          });
        } catch (err) {
          this.publishCrashDataError = errorParser(err);
        }
      }

      // Publish TestCase
      if (this.entry.testcase && !this.notAttachTest) {
        try {
          let content = this.testCaseContent;
          // If the testcase is binary we need to download it first
          if (this.entry.testcase_isbinary) {
            content = await api.retrieveCrashTestCaseBinary(this.entry.id);
          }

          payload = {
            ids: [this.createdBugId],
            data: this.entry.testcase_isbinary
              ? Base64.fromUint8Array(content)
              : Base64.encode(content),
            file_name: this.entry.testcase,
            summary: "Testcase",
            content_type: this.entry.testcase_isbinary
              ? "application/octet-stream"
              : "text/plain",
          };

          await bugzillaApi.createAttachment({
            hostname: this.provider.hostname,
            id: this.createdBugId,
            ...payload,
            headers: { "X-BUGZILLA-API-KEY": this.bugzillaToken },
          });
        } catch (err) {
          this.publishTestCaseError = errorParser(err);
        }
      }
    },
    async assignExternalBug() {
      const payload = {
        bug: this.createdBugId,
        bug_provider: this.provider.id,
      };
      try {
        await api.updateBucket({
          id: this.bucketId,
          params: { reassign: false },
          ...payload,
        });
      } catch (err) {
        this.assignError = errorParser(err);
      }
    },
  },
  watch: {
    selectedProvider() {
      this.provider = this.providers.find(
        (p) => p.id === this.selectedProvider
      );
    },
    selectedTemplate() {
      this.template = this.templates.find(
        (t) => t.id === this.selectedTemplate
      );
      this.updateFields();
    },
  },
};
</script>

<style scoped></style>
