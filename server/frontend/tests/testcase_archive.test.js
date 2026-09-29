import { TextDecoder, TextEncoder } from "util";
import JSZip from "jszip";
import { Base64 } from "js-base64";
import { shallowMount, flushPromises } from "@vue/test-utils";
import PublicationForm from "../src/components/Bugs/PublicationForm.vue";
import CommentForm from "../src/components/Bugs/Comments/PublicationForm.vue";
import TestCaseSection from "../src/components/Bugs/TestCaseSection.vue";
import * as api from "../src/api";
import * as bugzillaApi from "../src/bugzilla_api";
import {
  loadTestcaseArchive,
  archiveAttachmentPayloads,
} from "../src/testcase_archive";

jest.mock("../src/api");
jest.mock("../src/bugzilla_api");
jest.mock("mime", () => ({
  getType: (name) =>
    name.endsWith(".gif")
      ? "image/gif"
      : name.endsWith(".json")
        ? "application/json"
        : "text/html",
}));

global.TextDecoder = TextDecoder;
global.TextEncoder = TextEncoder;

const template = (mode) => ({
  id: 1,
  mode,
  name: "Template",
  testcase_filename: "testcase",
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

const makeZip = async () => {
  const zip = new JSZip();
  zip.file("testcase.html", "<h1>original</h1>");
  zip.file("test_info.json", '{"ok":true}');
  zip.file("image.gif", new Uint8Array([71, 73, 70, 56, 57, 97, 0, 255]));
  return zip.generateAsync({ type: "uint8array" });
};

beforeEach(async () => {
  jest.resetAllMocks();
  api.listBugProviders.mockResolvedValue({
    results: [
      { id: 1, classname: "BugzillaProvider", hostname: "bugs.example.com" },
    ],
  });
  api.listTemplates.mockResolvedValue({
    results: [template("bug"), template("comment")],
  });
  api.retrieveCrash.mockResolvedValue({
    id: 1,
    testcase: "tests/testcase.zip",
    testcase_isbinary: true,
    rawStderr: "crash",
    shortSignature: "Crash",
    os: "linux",
    platform: "x86-64",
  });
  api.retrieveCrashTestCaseBinary.mockResolvedValue(await makeZip());
  bugzillaApi.createBug.mockResolvedValue({ id: 123 });
  bugzillaApi.createComment.mockResolvedValue({ id: 456 });
  bugzillaApi.retrieveComment.mockResolvedValue({
    comments: { 456: { count: 2 } },
  });
});

const mountForm = async (Component, props = {}) => {
  const wrapper = shallowMount(Component, {
    props: { providerId: 1, templateId: 1, entryId: 1, bucketId: 1, ...props },
    global: { stubs: { TestCaseSection: false } },
  });
  await flushPromises();
  return wrapper;
};

test("ZIP checkbox appears only while attaching a ZIP testcase", async () => {
  const wrapper = shallowMount(TestCaseSection, {
    props: {
      entry: { id: 1, testcase: "testcase.zip", testcase_isbinary: true },
      template: {},
      fileName: "testcase",
    },
  });
  expect(wrapper.find("#id_testcase_unpack").exists()).toBe(true);
  await wrapper.get("#id_testcase_skip").setValue(true);
  expect(wrapper.find("#id_testcase_unpack").exists()).toBe(false);
  await wrapper.setProps({
    entry: { id: 1, testcase: "testcase.html", testcase_isbinary: false },
  });
  await wrapper.get("#id_testcase_skip").setValue(false);
  expect(wrapper.find("#id_testcase_unpack").exists()).toBe(false);
});

test("archive cards keep basenames editable and summarize included files", async () => {
  api.listTemplates.mockResolvedValue({ results: [template("bug")] });
  const wrapper = await mountForm(PublicationForm);
  await wrapper.get("#id_testcase_unpack").setValue(true);
  await flushPromises();

  expect(wrapper.findAll(".archive-card")).toHaveLength(3);
  expect(wrapper.get(".archive-count").text()).toBe(
    "3 of 3 files will be attached",
  );
  expect(wrapper.get("#archive_basename_0").element.value).toBe("testcase");
  expect(wrapper.get("#archive_extension_0").text()).toBe("HTML");
  expect(wrapper.findAll(".archive-content")).toHaveLength(2);
  expect(wrapper.findAll(".archive-content")[0].element.open).toBe(true);
  expect(wrapper.findAll(".archive-content")[1].element.open).toBe(false);

  await wrapper.get("#archive_basename_0").setValue("renamed");
  expect(wrapper.get("#archive_basename_0").element.value).toBe("renamed");
  await wrapper.get("#archive_skip_2").setValue(true);
  expect(wrapper.get(".archive-count").text()).toBe(
    "2 of 3 files will be attached",
  );
  expect(wrapper.findAll(".archive-card")[2].classes()).toContain(
    "archive-card-excluded",
  );
  wrapper.unmount();
});

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s publishes edited text and original binary files separately",
  async (mode, Component) => {
    api.listTemplates.mockResolvedValue({ results: [template(mode)] });
    const wrapper = await mountForm(Component);
    await wrapper.get("#id_testcase_unpack").setValue(true);
    await flushPromises();
    expect(wrapper.findAll('[id^="archive_basename_"]')).toHaveLength(3);
    expect(wrapper.findAll('[id^="archive_content_"]')).toHaveLength(2);
    expect(wrapper.findAll('[id^="archive_skip_"]')).toHaveLength(3);
    expect(
      wrapper
        .findAll('[id^="archive_skip_"]')
        .every((box) => !box.element.checked),
    ).toBe(true);
    await wrapper.get("#archive_basename_0").setValue("renamed");
    await wrapper.get("#archive_content_0").setValue("<h1>edited</h1>");

    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.createExternalComment();

    const attachments = bugzillaApi.createAttachment.mock.calls.map(
      ([payload]) => payload,
    );
    expect(attachments).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          file_name: "renamed.html",
          data: Base64.encode("<h1>edited</h1>"),
        }),
        expect.objectContaining({
          file_name: "test_info.json",
          data: Base64.encode('{"ok":true}'),
        }),
        expect.objectContaining({
          file_name: "image.gif",
          content_type: "image/gif",
          data: Base64.fromUint8Array(
            new Uint8Array([71, 73, 70, 56, 57, 97, 0, 255]),
          ),
        }),
      ]),
    );
    expect(
      attachments.filter((item) => item.file_name !== "crash_data.txt"),
    ).toHaveLength(3);
    expect(attachments.some((item) => item.file_name === "testcase.zip")).toBe(
      false,
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])(
  "%s omits individually checked ZIP files from attachments and rendered names",
  async (mode, Component) => {
    const selectedTemplate = template(mode);
    selectedTemplate.description = "{{testcase_attachment}}";
    selectedTemplate.comment = "{{testcase_attachment}}";
    api.listTemplates.mockResolvedValue({ results: [selectedTemplate] });
    const wrapper = await mountForm(Component);
    await wrapper.get("#id_testcase_unpack").setValue(true);
    await flushPromises();
    await wrapper.get("#archive_skip_1").setValue(true);
    // An excluded file is not validated for upload.
    await wrapper.get("#archive_basename_1").setValue("");
    const rendered =
      mode === "bug"
        ? wrapper.vm.renderedDescription
        : wrapper.vm.renderedComment;
    expect(rendered).toBe("testcase.html, image.gif");

    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.createExternalComment();
    const testcaseUploads = bugzillaApi.createAttachment.mock.calls
      .map(([payload]) => payload.file_name)
      .filter((name) => name !== "crash_data.txt");
    expect(testcaseUploads).toEqual(["testcase.html", "image.gif"]);
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm],
  ["comment", CommentForm],
])("%s allows every ZIP file to be excluded", async (mode, Component) => {
  const selectedTemplate = template(mode);
  selectedTemplate.description = "{{testcase_attachment}}";
  selectedTemplate.comment = "{{testcase_attachment}}";
  selectedTemplate.keywords =
    "{{#if isTestAttached}}attached{{else}}none{{/if}}";
  api.listTemplates.mockResolvedValue({ results: [selectedTemplate] });
  const wrapper = await mountForm(Component);
  await wrapper.get("#id_testcase_unpack").setValue(true);
  await flushPromises();
  for (const box of wrapper.findAll('[id^="archive_skip_"]'))
    await box.setValue(true);
  expect(
    mode === "bug"
      ? wrapper.vm.renderedDescription
      : wrapper.vm.renderedComment,
  ).toBe("");
  if (mode === "bug") expect(wrapper.vm.renderedKeywords).toBe("none");

  if (mode === "bug") await wrapper.vm.createExternalBug();
  else await wrapper.vm.createExternalComment();
  const testcaseUploads = bugzillaApi.createAttachment.mock.calls
    .map(([payload]) => payload.file_name)
    .filter((name) => name !== "crash_data.txt");
  expect(testcaseUploads).toEqual([]);
  wrapper.unmount();
});

test("a failed archive attachment reports its filename and continues uploading", async () => {
  api.listTemplates.mockResolvedValue({ results: [template("bug")] });
  bugzillaApi.createAttachment.mockImplementation(({ file_name }) =>
    file_name === "test_info.json"
      ? Promise.reject(new Error("upload rejected"))
      : Promise.resolve({}),
  );
  const wrapper = await mountForm(PublicationForm);
  await wrapper.get("#id_testcase_unpack").setValue(true);
  await flushPromises();
  await wrapper.vm.createExternalBug();
  expect(wrapper.vm.publishTestCaseError).toContain(
    "test_info.json: upload rejected",
  );
  expect(bugzillaApi.createAttachment).toHaveBeenCalledWith(
    expect.objectContaining({ file_name: "image.gif" }),
  );
  wrapper.unmount();
});

test.each([
  ["bug", PublicationForm, "createBug", false],
  ["bug", PublicationForm, "createBug", true],
  ["comment", CommentForm, "createComment", false],
  ["comment", CommentForm, "createComment", true],
])(
  "%s keeps the initial unpack choice %s while creation is pending",
  async (mode, Component, createCall, initiallyUnpacked) => {
    api.listTemplates.mockResolvedValue({ results: [template(mode)] });
    let releaseCreate;
    bugzillaApi[createCall].mockReturnValue(
      new Promise((resolve) => {
        releaseCreate = resolve;
      }),
    );
    const wrapper = await mountForm(Component);
    if (initiallyUnpacked) {
      await wrapper.get("#id_testcase_unpack").setValue(true);
      await flushPromises();
    }
    const publishing =
      mode === "bug"
        ? wrapper.vm.createExternalBug()
        : wrapper.vm.createExternalComment();
    await flushPromises();
    expect(wrapper.get("#id_testcase_unpack").element.disabled).toBe(true);
    // Exercise the upload snapshot even if reactive state changes after submit.
    wrapper.vm.testcaseArchive.enabled = !initiallyUnpacked;
    releaseCreate({ id: mode === "bug" ? 123 : 456 });
    await publishing;
    const testcaseUploads = bugzillaApi.createAttachment.mock.calls
      .map(([payload]) => payload.file_name)
      .filter((name) => name !== "crash_data.txt");
    expect(testcaseUploads).toEqual(
      initiallyUnpacked
        ? ["testcase.html", "test_info.json", "image.gif"]
        : ["testcase.zip"],
    );
    wrapper.unmount();
  },
);

test.each([
  ["bug", PublicationForm, "createBug"],
  ["comment", CommentForm, "createComment"],
])(
  "%s blocks publication when the ZIP is invalid",
  async (mode, Component, createCall) => {
    api.listTemplates.mockResolvedValue({ results: [template(mode)] });
    api.retrieveCrashTestCaseBinary.mockResolvedValue(
      new Uint8Array([1, 2, 3]),
    );
    const wrapper = await mountForm(Component);
    await wrapper.get("#id_testcase_unpack").setValue(true);
    await flushPromises();
    expect(wrapper.text()).toContain("Unable to unpack ZIP archive");
    if (mode === "bug") await wrapper.vm.createExternalBug();
    else await wrapper.vm.createExternalComment();
    expect(bugzillaApi[createCall]).not.toHaveBeenCalled();
    wrapper.unmount();
  },
);

test("archive preview recognizes extensionless text and keeps control bytes binary", async () => {
  const zip = new JSZip();
  zip.file("README", "plain text");
  zip.file(".config", "configuration");
  zip.file("binary", new Uint8Array([65, 0, 66]));
  api.retrieveCrashTestCaseBinary.mockResolvedValue(
    await zip.generateAsync({ type: "uint8array" }),
  );
  const files = await loadTestcaseArchive(1);
  expect(
    files.map(({ basename, extension, text }) => ({
      basename,
      extension,
      text,
    })),
  ).toEqual([
    { basename: "README", extension: null, text: "plain text" },
    { basename: ".config", extension: null, text: "configuration" },
    { basename: "binary", extension: null, text: null },
  ]);
});

test("untouched UTF-8 text retains its original bytes, including a BOM", async () => {
  const originalBytes = new Uint8Array([0xef, 0xbb, 0xbf, 0x41]);
  const zip = new JSZip();
  zip.file("bom.txt", originalBytes);
  api.retrieveCrashTestCaseBinary.mockResolvedValue(
    await zip.generateAsync({ type: "uint8array" }),
  );
  const [file] = await loadTestcaseArchive(1);
  expect(archiveAttachmentPayloads([file], "Testcase")[0].data).toBe(
    Base64.fromUint8Array(originalBytes),
  );
  file.text = "edited";
  expect(archiveAttachmentPayloads([file], "Testcase")[0].data).toBe(
    Base64.encode("edited"),
  );
});

test("an empty ZIP blocks publication and skipping the testcase clears the block", async () => {
  const zip = new JSZip();
  zip.folder("directory");
  api.retrieveCrashTestCaseBinary.mockResolvedValue(
    await zip.generateAsync({ type: "uint8array" }),
  );
  api.listTemplates.mockResolvedValue({ results: [template("bug")] });
  const wrapper = await mountForm(PublicationForm);
  await wrapper.get("#id_testcase_unpack").setValue(true);
  await flushPromises();
  expect(wrapper.text()).toContain("contains no files");
  await wrapper.vm.createExternalBug();
  expect(bugzillaApi.createBug).not.toHaveBeenCalled();
  await wrapper.get("#id_testcase_skip").setValue(true);
  await wrapper.vm.createExternalBug();
  expect(bugzillaApi.createBug).toHaveBeenCalledTimes(1);
  wrapper.unmount();
});
