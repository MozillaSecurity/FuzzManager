import { shallowMount, flushPromises } from "@vue/test-utils";
import PublicationForm from "../src/components/Bugs/PublicationForm.vue";
import CommentForm from "../src/components/Bugs/Comments/PublicationForm.vue";
import TestCaseSection from "../src/components/Bugs/TestCaseSection.vue";
import * as api from "../src/api";
import * as bugzillaApi from "../src/bugzilla_api";

jest.mock("../src/api");
jest.mock("../src/bugzilla_api");
jest.mock("mime", () => ({ getType: () => "text/plain" }));

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
  api.retrieveCrashTestCase.mockResolvedValue("test content");
  bugzillaApi.createBug.mockResolvedValue({ id: 123 });
});

const mountForm = async (Component, props) => {
  const wrapper = shallowMount(Component, {
    props: { providerId: 1, templateId: 1, entryId: 1, bucketId: 1, ...props },
    global: { stubs: { TestCaseSection: false } },
  });
  await flushPromises();
  return wrapper;
};

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
    expect(wrapper.get("#file_extension").element.value).toBe("html");
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
