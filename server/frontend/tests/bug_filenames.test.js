import { shallowMount, flushPromises } from "@vue/test-utils";
import { Base64 } from "js-base64";
import { TextDecoder, TextEncoder } from "util";
import PublicationForm from "../src/components/Bugs/PublicationForm.vue";
import CommentForm from "../src/components/Bugs/Comments/PublicationForm.vue";
import TestCaseSection from "../src/components/Bugs/TestCaseSection.vue";
import * as api from "../src/api";
import * as bugzillaApi from "../src/bugzilla_api";

jest.mock("../src/api");
jest.mock("../src/bugzilla_api");
jest.mock("mime", () => ({
  getType: (name) => (name.endsWith(".html") ? "text/html" : null),
}));

global.TextDecoder = TextDecoder;
global.TextEncoder = TextEncoder;

const template = (id, basename, mode = "bug") => ({
  id,
  mode,
  name: `Template ${id}`,
  testcase_filename: basename,
  product: "Firefox",
  component: "General",
  version: "unspecified",
  summary: "Crash",
  description: "",
  comment: "",
  attrs: "",
  cc: "",
  blocks: "",
  dependson: "",
  keywords: "",
  whiteboard: "",
});

beforeEach(() => {
  jest.resetAllMocks();
  api.listBugProviders.mockResolvedValue({
    results: [
      { id: 1, classname: "BugzillaProvider", hostname: "bugs.example.com" },
    ],
  });
  api.retrieveCrash.mockResolvedValue({
    id: 1,
    testcase: "tests/original.html",
    testcase_isbinary: false,
    rawStderr: "crash",
    shortSignature: "Crash",
    os: "linux",
    platform: "x86-64",
  });
  api.retrieveCrashTestCaseBinary.mockResolvedValue(
    new TextEncoder().encode("test content"),
  );
  bugzillaApi.createBug.mockResolvedValue({ id: 123 });
});

const mountForm = async (Component, props) => {
  const wrapper = shallowMount(Component, {
    props: { providerId: 1, templateId: 1, entryId: 1, bucketId: 1, ...props },
    global: { stubs: { TestCaseSection: false, TestcaseFileCard: false } },
  });
  await flushPromises();
  return wrapper;
};

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s displays a regular HTML testcase and attaches its edits",
  async (mode, Component) => {
    const html = "<!doctype html>\n<h1>original testcase</h1>";
    api.retrieveCrashTestCaseBinary.mockResolvedValue(
      new TextEncoder().encode(html),
    );
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.get("#id_testcase_content").element.value).toBe(html);
    expect(wrapper.get("#id_testcase_content").element.readOnly).toBe(false);
    await wrapper
      .get("#id_testcase_content")
      .setValue("<h1>edited testcase</h1>");
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        file_name: "testcase.html",
        data: Base64.encode("<h1>edited testcase</h1>"),
      }),
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s edits UTF-8 HTML marked binary because of vertical tabs",
  async (mode, Component) => {
    const crash = await api.retrieveCrash();
    crash.testcase_isbinary = true;
    const original = "<!doctype html>\n<p>one\vtwo\vthree</p>";
    api.retrieveCrashTestCaseBinary.mockResolvedValue(
      new TextEncoder().encode(original),
    );
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.get("#id_testcase_content").element.value).toBe(original);
    await wrapper.get("#id_testcase_content").setValue("<p>edited</p>");
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        file_name: "testcase.html",
        data: Base64.encode("<p>edited</p>"),
      }),
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s preserves untouched HTML bytes including BOM and CRLF",
  async (mode, Component) => {
    const crash = await api.retrieveCrash();
    crash.testcase_isbinary = true;
    const bytes = new TextEncoder().encode(
      "\uFEFF<!doctype html>\r\n<p>one\vtwo</p>",
    );
    api.retrieveCrashTestCaseBinary.mockResolvedValue(bytes);
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.find("#id_testcase_content").exists()).toBe(true);
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({ data: Base64.fromUint8Array(bytes) }),
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s preserves HTML bytes that cannot be decoded as UTF-8",
  async (mode, Component) => {
    const crash = await api.retrieveCrash();
    crash.testcase_isbinary = true;
    const bytes = new Uint8Array([0xff, 0xfe, 0x41]);
    api.retrieveCrashTestCaseBinary.mockResolvedValue(bytes);
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.find("#id_testcase_content").exists()).toBe(false);
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({ data: Base64.fromUint8Array(bytes) }),
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s uses one exclusion control for a single file and restores edits",
  async (mode, Component) => {
    const selectedTemplate = template(1, "testcase", mode);
    selectedTemplate.description = "{{testcase_attachment}}";
    selectedTemplate.comment = "{{testcase_attachment}}";
    api.listTemplates.mockResolvedValue({ results: [selectedTemplate] });
    const wrapper = await mountForm(Component);
    expect(wrapper.findAll(".archive-card")).toHaveLength(1);
    expect(wrapper.get(".archive-content").element.open).toBe(true);
    expect(wrapper.find("#id_testcase_file_skip").exists()).toBe(false);
    expect(wrapper.get("#id_testcase_skip").element.checked).toBe(false);
    await wrapper.get("#id_testcase_filename").setValue("edited-name");
    await wrapper.get("#id_testcase_content").setValue("edited contents");
    await wrapper.get("#id_testcase_skip").setValue(true);
    expect(wrapper.find(".archive-card").exists()).toBe(false);
    expect(wrapper.find("#id_testcase_content").exists()).toBe(false);
    expect(wrapper.find(".archive-count").exists()).toBe(false);
    expect(
      mode === "bug"
        ? wrapper.vm.renderedDescription
        : wrapper.vm.renderedComment,
    ).toBe("");
    await wrapper.get("#id_testcase_skip").setValue(false);
    expect(wrapper.get("#id_testcase_filename").element.value).toBe(
      "edited-name",
    );
    expect(wrapper.get("#id_testcase_content").element.value).toBe(
      "edited contents",
    );
    expect(wrapper.get(".archive-content").element.open).toBe(true);
    await wrapper.get("#id_testcase_skip").setValue(true);
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(
      bugzillaApi.createAttachment.mock.calls.map(([p]) => p.file_name),
    ).toEqual(["crash_data.txt"]);
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s blocks creation until the single testcase loads",
  async (mode, Component) => {
    let resolveDownload;
    api.retrieveCrashTestCaseBinary.mockReturnValue(
      new Promise((resolve) => {
        resolveDownload = resolve;
      }),
    );
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.get("#id_testcase_filename").element.disabled).toBe(true);
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.createExternalComment();
    expect(
      mode === "bug" ? bugzillaApi.createBug : bugzillaApi.createComment,
    ).not.toHaveBeenCalled();
    expect(wrapper.vm.createError).toContain("Wait for the testcase to load");
    resolveDownload(new TextEncoder().encode("contents"));
    await flushPromises();
    expect(wrapper.get("#id_testcase_content").element.value).toBe("contents");
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s snapshots the single testcase edits before creation",
  async (mode, Component) => {
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    let resolveCreate;
    const createCall =
      mode === "bug" ? bugzillaApi.createBug : bugzillaApi.createComment;
    createCall.mockReturnValue(
      new Promise((resolve) => {
        resolveCreate = resolve;
      }),
    );
    bugzillaApi.retrieveComment.mockResolvedValue({
      comments: { 456: { count: 2 } },
    });
    const wrapper = await mountForm(Component);
    await wrapper.get("#id_testcase_content").setValue("before submit");
    const publishing =
      mode === "bug"
        ? wrapper.vm.createExternalBug()
        : wrapper.vm.createExternalComment();
    await flushPromises();
    expect(wrapper.get("#id_testcase_skip").element.disabled).toBe(true);
    wrapper.vm.testcaseFiles.files[0].text = "after submit";
    wrapper.vm.notAttachTest = true;
    resolveCreate({ id: mode === "bug" ? 123 : 456 });
    await publishing;
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        file_name: "testcase.html",
        data: Base64.encode("before submit"),
      }),
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s can exclude a single testcase whose download failed",
  async (mode, Component) => {
    api.retrieveCrashTestCaseBinary.mockRejectedValue(
      new Error("download failed"),
    );
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.text()).toContain("Unable to load testcase contents");
    await wrapper.get("#id_testcase_skip").setValue(true);
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(
      bugzillaApi.createAttachment.mock.calls.map(([p]) => p.file_name),
    ).toEqual(["crash_data.txt"]);
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])("%s retries a failed single testcase download", async (mode, Component) => {
  let resolveRetry;
  api.retrieveCrashTestCaseBinary
    .mockRejectedValueOnce(new Error("temporary failure"))
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveRetry = resolve;
        }),
    );
  api.listTemplates.mockResolvedValue({
    results: [template(1, "testcase", mode)],
  });
  const wrapper = await mountForm(Component);
  expect(wrapper.text()).toContain("Unable to load testcase contents");
  await wrapper.get(".alert-danger button").trigger("click");
  expect(api.retrieveCrashTestCaseBinary).toHaveBeenCalledTimes(2);
  expect(wrapper.find(".alert-danger").exists()).toBe(false);
  expect(wrapper.get("#id_testcase_filename").element.disabled).toBe(true);
  if (mode === "bug") await wrapper.vm.createExternalBug();
  else await wrapper.vm.createExternalComment();
  expect(
    mode === "bug" ? bugzillaApi.createBug : bugzillaApi.createComment,
  ).not.toHaveBeenCalled();
  resolveRetry(new TextEncoder().encode("recovered contents"));
  await flushPromises();
  expect(wrapper.get("#id_testcase_content").element.value).toBe(
    "recovered contents",
  );
  if (mode === "bug") await wrapper.vm.createExternalBug();
  else await wrapper.vm.publishAttachments();
  expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
    expect.objectContaining({ data: Base64.encode("recovered contents") }),
  );
  wrapper.unmount();
});

test.each(["testcase", "testcase.min", ""])(
  "template saves basename %j without the example ZIP extension",
  async (basename) => {
    api.listTemplates.mockResolvedValue({ results: [template(1, basename)] });
    // Stop after capturing the request, before browser navigation.
    api.updateBugzillaBugTemplate.mockRejectedValue(
      new Error("stop navigation"),
    );
    const wrapper = await mountForm(PublicationForm, {
      isBugTemplateCreation: true,
    });
    expect(wrapper.get("#testcase_filename").element.value).toBe(basename);
    expect(wrapper.find("#file_extension").exists()).toBe(false);
    await wrapper.vm.createOrUpdateBugzillaBugTemplate();
    expect(api.updateBugzillaBugTemplate).toHaveBeenCalledWith(
      1,
      expect.any(FormData),
    );
    expect(
      api.updateBugzillaBugTemplate.mock.calls[0][1].get("testcase_filename"),
    ).toBe(basename);
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s uses the selected template basename in the displayed field and attachment",
  async (mode, Component) => {
    api.listTemplates.mockResolvedValue({
      results: [template(1, "testcase", mode), template(2, "repro.min", mode)],
    });
    const wrapper = await mountForm(Component);
    expect(wrapper.get("#id_testcase_filename").element.value).toBe("testcase");
    await wrapper.get("#id_testcase_filename").setValue("custom");
    expect(wrapper.vm.filenameWithExtension).toBe("custom.html");
    await wrapper.get("#bt_select").setValue("2");
    expect(wrapper.get("#id_testcase_filename").element.value).toBe(
      "repro.min",
    );
    expect(wrapper.get("#file_extension").text()).toBe("HTML");
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.publishAttachments();
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        file_name: "repro.min.html",
      }),
    );
    wrapper.unmount();
  },
);

test("filename input follows prop changes without emitting an edit", async () => {
  const wrapper = shallowMount(TestCaseSection, {
    global: { stubs: { TestcaseFileCard: false } },
    props: {
      entry: { testcase_isbinary: true },
      template: {},
      fileName: "testcase",
      fileExtension: "html",
    },
  });
  await flushPromises();
  expect(wrapper.emitted("update-filename")).toBeUndefined();
  await wrapper.setProps({ fileName: "repro" });
  expect(wrapper.get("#id_testcase_filename").element.value).toBe("repro");
  expect(wrapper.emitted("update-filename")).toBeUndefined();
  await wrapper.get("#id_testcase_filename").setValue("custom");
  expect(wrapper.emitted("update-filename")).toEqual([["custom"]]);
});

test("new templates store only the entered basename", async () => {
  api.createBugzillaBugTemplate.mockRejectedValue(new Error("stop navigation"));
  const wrapper = await mountForm(PublicationForm, {
    isBugTemplateCreation: true,
    templateId: null,
  });
  expect(wrapper.get("#testcase_filename").element.value).toBe("");
  wrapper.vm.template.name = "New template";
  wrapper.vm.template.version = "unspecified";
  wrapper.vm.product = "Firefox";
  wrapper.vm.component = "General";
  await wrapper.get("#testcase_filename").setValue("testcase.min");
  await wrapper.vm.createOrUpdateBugzillaBugTemplate();
  expect(api.createBugzillaBugTemplate).toHaveBeenCalledTimes(1);
  expect(
    api.createBugzillaBugTemplate.mock.calls[0][0].get("testcase_filename"),
  ).toBe("testcase.min");
  wrapper.unmount();
});

test.each(["js", "zip", "bin", ""])(
  "filing preserves the original extension %j",
  async (extension) => {
    const crash = await api.retrieveCrash();
    crash.testcase = extension
      ? `tests/original.${extension}`
      : "tests/original";
    api.listTemplates.mockResolvedValue({ results: [template(1, "testcase")] });
    const wrapper = await mountForm(PublicationForm);
    await wrapper.vm.createExternalBug();
    expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
      expect.objectContaining({
        file_name: extension ? `testcase.${extension}` : "testcase",
      }),
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])("%s filing supports crashes without a testcase", async (mode, Component) => {
  const crash = await api.retrieveCrash();
  crash.testcase = null;
  api.listTemplates.mockResolvedValue({
    results: [template(1, "testcase", mode)],
  });
  const wrapper = await mountForm(Component);
  expect(wrapper.find("#id_testcase_filename").exists()).toBe(false);
  if (mode === "bug") await wrapper.vm.createExternalBug();
  else await wrapper.vm.publishAttachments();
  expect(bugzillaApi.createAttachment).toHaveBeenCalledTimes(1);
  expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
    expect.objectContaining({ file_name: "crash_data.txt" }),
  );
  wrapper.unmount();
});
