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
            v-model="selectedProvider"
            class="form-control"
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
        You are about to submit this bug to
        <strong>{{ provider.hostname }}</strong>
      </div>
      <hr />

      <h3>Create a bug for crash {{ entryId }}</h3>
      <div v-if="!template" class="alert alert-info" role="alert">
        Please pick a bug template to file a new bug.
      </div>
      <form v-else>
        <SummaryInput
          v-if="provider"
          :initial-summary="summary"
          :bucket-id="bucketId"
          :provider="provider"
          @update-summary="summary = $event"
        />

        <div class="row">
          <ProductComponentSelect
            v-if="provider"
            :provider-hostname="provider.hostname"
            :template-product="template.product"
            :template-component="template.component"
            @update-product="product = $event"
            @update-component="component = $event"
          />
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="op_sys">OS</label>
            <input
              id="id_op_sys"
              v-model="opSys"
              class="form-control"
              maxlength="1023"
              name="op_sys"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="platform">Platform</label>
            <input
              id="id_platform"
              v-model="platform"
              class="form-control"
              maxlength="1023"
              name="platform"
              type="text"
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
              @update-value="template.cc = $event"
            />
            <input
              v-else
              id="id_cc"
              v-model="template.cc"
              class="form-control"
              maxlength="1023"
              name="cc"
              type="text"
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
              @update-value="template.assigned_to = $event"
            />
            <input
              v-else
              id="id_assigned_to"
              v-model="template.assigned_to"
              class="form-control"
              maxlength="1023"
              name="assigned_to"
              type="text"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="priority">Priority</label>
            <input
              id="id_priority"
              v-model="template.priority"
              class="form-control"
              maxlength="1023"
              name="priority"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="severity">Severity</label>
            <input
              id="id_severity"
              v-model="template.severity"
              class="form-control"
              maxlength="1023"
              name="severity"
              type="text"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="alias">Alias</label>
            <input
              id="id_alias"
              v-model="template.alias"
              class="form-control"
              maxlength="1023"
              name="alias"
              type="text"
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
              @update-value="template.qa_contact = $event"
            />
            <input
              v-else
              id="id_qa_contact"
              v-model="template.qa_contact"
              class="form-control"
              maxlength="1023"
              name="qa_contact"
              type="text"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="status">Status</label>
            <input
              id="id_status"
              v-model="template.status"
              class="form-control"
              maxlength="1023"
              name="status"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="resolution">Resolution</label>
            <input
              id="id_resolution"
              v-model="template.resolution"
              class="form-control"
              maxlength="1023"
              name="resolution"
              type="text"
            />
          </div>
        </div>

        <div class="row">
          <div class="form-group col-md-6">
            <label for="version">Version</label>
            <input
              id="id_version"
              v-model="template.version"
              class="form-control"
              maxlength="1023"
              name="version"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="target_milestone">Target milestone</label>
            <input
              id="id_target_milestone"
              v-model="template.target_milestone"
              class="form-control"
              maxlength="1023"
              name="target_milestone"
              type="text"
            />
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="dependson">Depends On</label>
            <input
              id="id_dependson"
              v-model="template.dependson"
              class="form-control"
              maxlength="1023"
              name="dependson"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="blocks">Blocks</label>
            <input
              id="id_blocks"
              v-model="template.blocks"
              class="form-control"
              maxlength="1023"
              name="blocks"
              type="text"
            />
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="whiteboard">Whiteboard</label>
            <HelpPopover
              field="keywords"
              :variables="['isTestAttached']"
              documentation-link="https://github.com/MozillaSecurity/FuzzManager/blob/master/doc/BugzillaVariables.md#in-custom-fields-field"
            />
            <input
              id="id_whiteboard"
              v-model="template.whiteboard"
              class="form-control"
              maxlength="1023"
              name="whiteboard"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="attrs">Rendered Whiteboard</label>
            <textarea
              id="id_rendered_whiteboard"
              class="form-control"
              name="rendered_whiteboard"
              readonly
              :value="renderedWhiteboard"
            ></textarea>
          </div>
        </div>
        <div class="row">
          <div class="form-group col-md-6">
            <label for="keywords">Keywords</label>
            <HelpPopover
              field="keywords"
              :variables="['isTestAttached']"
              documentation-link="https://github.com/MozillaSecurity/FuzzManager/blob/master/doc/BugzillaVariables.md#in-custom-fields-field"
            />
            <input
              id="id_keywords"
              v-model="template.keywords"
              class="form-control"
              maxlength="1023"
              name="keywords"
              type="text"
            />
          </div>
          <div class="form-group col-md-6">
            <label for="attrs">Rendered Keywords</label>
            <textarea
              id="id_rendered_keywords"
              class="form-control"
              name="rendered_keywords"
              readonly
              :value="renderedKeywords"
            ></textarea>
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
              v-model="template.attrs"
              class="form-control"
              name="attrs"
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
              v-model="template.description"
              class="form-control"
              name="description"
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
              id="id_security"
              v-model="template.security"
              type="checkbox"
              name="security"
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
              id="id_security_group"
              v-model="template.security_group"
              type="text"
              class="form-control"
              maxlength="1023"
              name="security_group"
              :disabled="!template.security"
            />
          </div>
        </div>
        <hr />

        <CrashDataSection
          :initial-not-attach-data="notAttachData"
          :initial-data="crashData"
          :path-prefix="entryMetadata.pathprefix"
          @update-not-attach-data="notAttachData = $event"
          @update-data="crashData = $event"
        />

        <TestCaseSection
          v-if="entry.testcase"
          :initial-not-attach-test="notAttachTest"
          :entry="entry"
          :template="template"
          @update-not-attach-test="notAttachTest = $event"
          @update-filename="entry.testcase = $event"
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
            @click="publishCrashDataError = null"
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
            @click="publishTestCaseError = null"
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
            @click="assignError = null"
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
            :disabled="!bugzillaToken || submitting"
            @click="createExternalBug"
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
import {
  computed,
  defineComponent,
  getCurrentInstance,
  onMounted,
  ref,
  watch,
} from "vue";
import * as api from "../../api";
import * as bugzillaApi from "../../bugzilla_api";
import * as HandlebarsHelpers from "../../handlebars_helpers";
import { errorParser } from "../../helpers";
import CrashDataSection from "./CrashDataSection.vue";
import HelpPopover from "./HelpPopover.vue";
import ProductComponentSelect from "./ProductComponentSelect.vue";
import SummaryInput from "./SummaryInput.vue";
import TestCaseSection from "./TestCaseSection.vue";
import UserDropdown from "./UserDropdown.vue";

// Apply Handlebars helpers
Object.entries(HandlebarsHelpers).forEach(([name, callback]) => {
  Handlebars.registerHelper(name, callback);
});

export default defineComponent({
  name: "PublicationForm",
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
  setup(props) {
    const providers = ref([]);
    const selectedProvider = ref(null);
    const provider = ref(null);
    const templates = ref([]);
    const selectedTemplate = ref(null);
    const template = ref(null);
    const entry = ref(null);
    const summary = ref("");
    const product = ref("");
    const component = ref("");
    const opSys = ref("");
    const platform = ref("");
    const submitting = ref(false);
    const createError = ref(null);
    const publishTestCaseError = ref(null);
    const publishCrashDataError = ref(null);
    const assignError = ref(null);
    const createdBugId = ref(null);
    const notAttachTest = ref(false);
    const testCaseContent = ref("");
    const notAttachData = ref(false);
    const crashData = ref("");

    const bugLink = computed(() => {
      return `https://${provider.value.hostname}/${createdBugId.value}`;
    });

    const bugzillaToken = computed(() => {
      return localStorage.getItem(
        "provider-" + provider.value?.id + "-api-key",
      );
    });

    const entryMetadata = computed(() => {
      if (entry.value && entry.value.metadata)
        return JSON.parse(entry.value.metadata);
      return {};
    });

    const preSummary = computed(() => {
      if (template.value?.summary) return template.value.summary;
      if (entry.value?.shortSignature?.startsWith("[@"))
        return "Crash " + entry.value.shortSignature;
      return entry.value?.shortSignature;
    });

    const crashDataRendered = computed(() => {
      return crashData.value
        .split("\n")
        .map((l) => "    " + l)
        .join("\n");
    });

    const testCaseRendered = computed(() => {
      if (!entry.value.testcase) return "(Test not available)";
      else if (testCaseContent.value.length > 2048) return "See attachment.";
      return testCaseContent.value
        .split("\n")
        .map((l) => "    " + l)
        .join("\n");
    });

    const renderedAttrs = computed(() => {
      if (!template.value || !entry.value) return "";
      try {
        const compiled = Handlebars.compile(template.value.attrs);
        let rendered = compiled({
          ...metadataExtension(template.value.attrs),
        });
        if (
          entry.value.shortSignature &&
          entry.value.shortSignature.startsWith("[@")
        )
          rendered += "\ncf_crash_signature=" + entry.value.shortSignature;
        return rendered;
      } catch {
        return "";
      }
    });

    const renderedDescription = computed(() => {
      if (!template.value || !entry.value) return "";
      try {
        const compiled = Handlebars.compile(template.value.description);
        let rendered = compiled({
          summary: summary.value,
          shortsig: entry.value.shortSignature,
          product: entry.value.product,
          version: entry.value.product_version
            ? entry.value.product_version
            : "(Version not available)",
          args: entry.value.args ? JSON.parse(entry.value.args).join(" ") : "",
          os: entry.value.os,
          platform: entry.value.platform,
          client: entry.value.client,
          testcase: testCaseRendered.value,
          crashdata: crashDataRendered.value,
          crashdataattached: notAttachData.value
            ? "(Crash data not available)"
            : "For detailed crash information, see attachment.",
          ...metadataExtension(template.value.description),
        });

        // Remove the specified pathPrefix from traces and assertion
        if (entryMetadata.value.pathprefix)
          rendered = rendered.replaceAll(entryMetadata.value.pathprefix, "");

        return rendered;
      } catch {
        return "";
      }
    });

    const renderedKeywords = computed(() => {
      if (!template.value || !entry.value) return "";
      try {
        const compiled = Handlebars.compile(template.value.keywords);
        return compiled({ isTestAttached: !notAttachTest.value });
      } catch {
        return "";
      }
    });

    const renderedWhiteboard = computed(() => {
      if (!template.value || !entry.value) return "";
      try {
        const compiled = Handlebars.compile(template.value.whiteboard);
        return compiled({ isTestAttached: !notAttachTest.value });
      } catch {
        return "";
      }
    });

    // Methods
    const goBack = () => {
      window.history.back();
    };

    const metadataExtension = (field) => {
      let extension = {};
      for (const [key, value] of Object.entries(entryMetadata.value)) {
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
    };

    const updateFields = () => {
      // Remove the specified pathPrefix from traces and assertion
      if (!entryMetadata.value.pathprefix) summary.value = preSummary.value;
      else
        summary.value = preSummary.value.replaceAll(
          entryMetadata.value.pathprefix,
          "",
        );

      // OpSys
      opSys.value = template.value.op_sys;
      if (!template.value.op_sys) {
        // Try to match the supplied os with the Bugzilla equivalent
        const os = entry.value.os.toLowerCase();
        if (os === "linux") opSys.value = "Linux";
        else if (os === "macosx") opSys.value = "macOS";
        else if (os === "windows") opSys.value = "Windows";
        else if (os === "android") opSys.value = "Android";
      }

      // Platform
      // BMO uses x86_64, not x86-64, and ARM instead of arm
      if (template.value.platform) platform.value = template.value.platform;
      else
        platform.value = entry.value.platform
          .replaceAll("-", "_")
          .replaceAll("arm", "ARM");
    };

    const createExternalBug = async () => {
      submitting.value = true;
      createdBugId.value = null;
      createError.value = null;
      publishTestCaseError.value = null;
      publishCrashDataError.value = null;
      assignError.value = null;

      // Convert this.renderedAttrs to an object
      const attrs = Object.fromEntries(
        renderedAttrs.value.split("\n").map((l) => l.split("=")),
      );

      let groups = [];
      if (template.value.security)
        groups = template.value.security_group
          ? [template.value.security_group]
          : ["core-security"];

      // Status ?? Resolution ??
      const rawPayload = {
        type: "defect",
        product: product.value,
        component: component.value,
        summary: summary.value,
        version: template.value.version,
        description: renderedDescription.value,
        op_sys: opSys.value,
        platform: platform.value,
        priority: template.value.priority,
        severity: template.value.severity,
        alias: template.value.alias,
        cc: template.value.cc.split(","),
        assigned_to: template.value.assigned_to,
        qa_contact: template.value.qa_contact,
        target_milestone: template.value.target_milestone,
        whiteboard: renderedWhiteboard.value,
        keywords: renderedKeywords.value,
        groups: groups.length ? groups : "",
        blocks: template.value.blocks.split(","),
        dependson: template.value.dependson.split(","),
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
          hostname: provider.value.hostname,
          ...cleanPayload,
          headers: { "X-BUGZILLA-API-KEY": bugzillaToken.value },
        });
        createdBugId.value = data.id;
        await assignExternalBug();
        await publishAttachments();
      } catch (err) {
        createError.value = errorParser(err);
      } finally {
        submitting.value = false;
      }
    };

    const publishAttachments = async () => {
      let payload = {};
      // Publish Crash data
      if (!notAttachData.value) {
        try {
          payload = {
            ids: [createdBugId.value],
            data: Base64.encode(crashData.value),
            file_name: "crash_data.txt",
            summary: "Detailed Crash Information",
            content_type: "text/plain",
          };

          await bugzillaApi.createAttachment({
            hostname: provider.value.hostname,
            id: createdBugId.value,
            ...payload,
            headers: { "X-BUGZILLA-API-KEY": bugzillaToken.value },
          });
        } catch (err) {
          publishCrashDataError.value = errorParser(err);
        }
      }

      // Publish TestCase
      if (entry.value.testcase && !notAttachTest.value) {
        try {
          let content = testCaseContent.value;
          // If the testcase is binary we need to download it first
          if (entry.value.testcase_isbinary) {
            content = await api.retrieveCrashTestCaseBinary(entry.value.id);
          }

          payload = {
            ids: [createdBugId.value],
            data: entry.value.testcase_isbinary
              ? Base64.fromUint8Array(content)
              : Base64.encode(content),
            file_name: entry.value.testcase,
            summary: "Testcase",
            content_type: entry.value.testcase_isbinary
              ? "application/octet-stream"
              : "text/plain",
          };

          await bugzillaApi.createAttachment({
            hostname: provider.value.hostname,
            id: createdBugId.value,
            ...payload,
            headers: { "X-BUGZILLA-API-KEY": bugzillaToken.value },
          });
        } catch (err) {
          publishTestCaseError.value = errorParser(err);
        }
      }
    };

    const instance = getCurrentInstance();
    const assignExternalBug = async () => {
      const payload = {
        bug: createdBugId.value,
        bug_provider: provider.value.id,
      };
      try {
        await api.updateBucket({
          id: instance.proxy.bucketId,
          params: { reassign: false },
          ...payload,
        });
      } catch (err) {
        assignError.value = errorParser(err);
      }
    };

    // Watchers
    watch(selectedProvider, () => {
      provider.value = providers.value.find(
        (p) => p.id === selectedProvider.value,
      );
    });

    watch(selectedTemplate, () => {
      template.value = templates.value.find(
        (t) => t.id === selectedTemplate.value,
      );
      updateFields();
    });

    const mounted = async () => {
      entry.value = await api.retrieveCrash(props.entryId);
      crashData.value = entry.value.rawCrashData
        ? entry.value.rawCrashData
        : entry.value.rawStderr;

      let data = await api.listBugProviders();
      providers.value = data.results.filter(
        (p) => p.classname === "BugzillaProvider",
      );
      provider.value = providers.value.find((p) => p.id === props.providerId);
      selectedProvider.value = provider.value.id;
      data = await api.listTemplates();
      templates.value = data.results.filter((t) => t.mode === "bug");
      template.value = templates.value.find((t) => t.id === props.templateId);
      if (template.value) {
        selectedTemplate.value = template.value.id;
        updateFields();
      }
    };

    onMounted(mounted);

    return {
      providers,
      selectedProvider,
      provider,
      templates,
      selectedTemplate,
      template,
      entry,
      summary,
      product,
      component,
      opSys,
      platform,
      submitting,
      createError,
      publishTestCaseError,
      publishCrashDataError,
      assignError,
      createdBugId,
      notAttachTest,
      testCaseContent,
      notAttachData,
      crashData,
      bugLink,
      bugzillaToken,
      entryMetadata,
      renderedDescription,
      renderedWhiteboard,
      renderedKeywords,
      renderedAttrs,
      goBack,
      createExternalBug,
    };
  },
});
</script>

<style scoped></style>
