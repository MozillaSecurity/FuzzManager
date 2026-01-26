import { parseFilename, buildFilename } from "../src/helpers";

describe("parseFilename", () => {
  test.each([
    [
      "testcase with file extension",
      "tests/test.txt",
      "testcase",
      { basename: "testcase", extension: "txt" },
    ],
    [
      "testcase without an extension",
      "tests/original",
      "template_name",
      { basename: "template_name", extension: null },
    ],
    [
      "testcase with no basename",
      "test/.bin",
      null,
      { basename: "", extension: "bin" },
    ],
    [
      "testcase with an extension (no template)",
      "tests/test.txt",
      null,
      { basename: "test", extension: "txt" },
    ],
    [
      "testcase without an extension (no template)",
      "tests/test",
      null,
      { basename: "test", extension: null },
    ],
    [
      "testcase with multiple dots (no template)",
      "test/test.min.js",
      null,
      { basename: "test.min", extension: "js" },
    ],
  ])("%s", (_description, testcasePath, templateBasename, expected) => {
    const result = parseFilename(testcasePath, templateBasename);
    expect(result).toEqual(expected);
  });
});

describe("buildFilename", () => {
  test.each([
    ["testcase with an extension", "test", "txt", "test.txt"],
    ["testcase without an extension", "test", null, "test"],
    ["testcase with an empty extension", "test", "", "test"],
    ["testcase with multiple dots", "test.min", "js", "test.min.js"],
    ["testcase with an empty basename", "", "bin", ".bin"],
  ])("%s", (_description, basename, extension, expected) => {
    const result = buildFilename(basename, extension);
    expect(result).toBe(expected);
  });
});
