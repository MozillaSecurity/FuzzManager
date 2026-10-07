import { Base64 } from "js-base64";
import mime from "mime";
import { buildFilename, parseFilename } from "./helpers";

function readableText(bytes, filename, knownText) {
  const type = mime.getType(filename);
  const textType =
    type?.startsWith("text/") ||
    [
      "application/json",
      "application/javascript",
      "application/xml",
      "application/xhtml+xml",
      "image/svg+xml",
    ].includes(type);
  // Control characters may be intentional in a text testcase. For unknown
  // formats, avoid treating a binary file as text merely because UTF-8 decodes.
  if (
    !knownText &&
    !textType &&
    bytes.some((byte) => byte < 32 && ![9, 10, 13].includes(byte))
  )
    return null;
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return null;
  }
}

export function createTestcaseFile(filename, bytes, knownText = false) {
  const originalName = filename.split(/[\\/]/).pop();
  const { basename, extension } =
    originalName.startsWith(".") && !originalName.slice(1).includes(".")
      ? { basename: originalName, extension: null }
      : parseFilename(originalName);
  const text = readableText(bytes, originalName, knownText);
  return {
    originalName,
    basename,
    extension,
    bytes,
    text,
    originalText: text,
    doNotAttach: false,
  };
}

export function testcaseAttachmentPayloads(files) {
  return files
    .filter((file) => !file.doNotAttach)
    .map((file) => {
      if (!file.basename?.trim())
        throw new Error(`Enter a basename for ${file.originalName}.`);
      if (!file.bytes)
        throw new Error(`Wait for ${file.originalName} to load.`);
      const fileName = buildFilename(file.basename, file.extension);
      return {
        file_name: fileName,
        summary: fileName,
        data:
          file.text === null || file.text === file.originalText
            ? Base64.fromUint8Array(file.bytes)
            : Base64.encode(file.text),
        content_type:
          mime.getType(fileName) ||
          (file.text === null ? "application/octet-stream" : "text/plain"),
      };
    });
}

export function testcaseAttachmentPlan(entry, skipped, state) {
  if (!entry?.testcase || skipped) return { payloads: [] };
  const { loading, error, files } = state;
  if (files.length && files.every((file) => file.doNotAttach)) {
    return { payloads: [] };
  }
  if (loading || error || !files.length)
    throw new Error(error || "Wait for the testcase to load.");
  return { payloads: testcaseAttachmentPayloads(files) };
}
