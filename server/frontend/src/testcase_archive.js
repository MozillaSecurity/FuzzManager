import JSZip from "jszip";
import { Base64 } from "js-base64";
import mime from "mime";
import * as api from "./api";
import { buildFilename, parseFilename } from "./helpers";

function readableText(bytes) {
  // A successful UTF-8 decode alone also accepts some binary file formats.
  if (bytes.some((byte) => byte < 32 && ![9, 10, 13].includes(byte))) {
    return null;
  }
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return null;
  }
}

export async function loadTestcaseArchive(entryId) {
  const data = await api.retrieveCrashTestCaseBinary(entryId);
  const archive = await JSZip.loadAsync(data, { checkCRC32: true });
  const files = [];

  for (const entry of Object.values(archive.files)) {
    if (entry.dir) continue;
    const originalName = entry.name.split(/[\\/]/).pop();
    if (!originalName) continue;
    const bytes = await entry.async("uint8array");
    const { basename, extension } =
      originalName.startsWith(".") && !originalName.slice(1).includes(".")
        ? { basename: originalName, extension: null }
        : parseFilename(originalName);
    const text = readableText(bytes);
    files.push({
      originalName,
      basename,
      extension,
      bytes,
      text,
      originalText: text,
      doNotAttach: false,
    });
  }

  if (!files.length) throw new Error("The ZIP archive contains no files.");
  return files;
}

export function archiveAttachmentPayloads(files, summary) {
  return files
    .filter((file) => !file.doNotAttach)
    .map((file) => {
      if (!file.basename.trim()) {
        throw new Error(`Enter a basename for ${file.originalName}.`);
      }
      const fileName = buildFilename(file.basename, file.extension);
      return {
        file_name: fileName,
        data:
          file.text === null || file.text === file.originalText
            ? Base64.fromUint8Array(file.bytes)
            : Base64.encode(file.text),
        summary,
        content_type:
          mime.getType(fileName) ||
          (file.text === null ? "application/octet-stream" : "text/plain"),
      };
    });
}
