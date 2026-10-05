import { Base64 } from "js-base64";
import mime from "mime";
import * as api from "./api";

export async function loadBinaryTextPreview(entry) {
  const type = entry.testcase ? mime.getType(entry.testcase) : null;
  if (
    !type?.startsWith("text/") &&
    ![
      "application/json",
      "application/javascript",
      "application/xml",
      "application/xhtml+xml",
      "image/svg+xml",
    ].includes(type)
  ) {
    return null;
  }
  const bytes = await api.retrieveCrashTestCaseBinary(entry.id);
  try {
    // The stored binary flag can also describe UTF-8 HTML with control characters.
    const originalText = new TextDecoder("utf-8", { fatal: true }).decode(
      bytes,
    );
    return { bytes, originalText };
  } catch {
    return null;
  }
}

export async function testcaseAttachmentData(entry, content, preview) {
  if (!entry.testcase_isbinary) return Base64.encode(content);
  if (preview && content !== preview.originalText)
    return Base64.encode(content);
  const bytes =
    preview?.bytes ?? (await api.retrieveCrashTestCaseBinary(entry.id));
  return Base64.fromUint8Array(bytes);
}
