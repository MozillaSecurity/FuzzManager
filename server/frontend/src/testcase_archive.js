import JSZip from "jszip";
import * as api from "./api";
import { createTestcaseFile } from "./testcase_files";

export async function loadTestcaseArchive(entryId, data = null) {
  const bytes = data ?? (await api.retrieveCrashTestCaseBinary(entryId));
  const archive = await JSZip.loadAsync(bytes, { checkCRC32: true });
  const files = [];
  for (const entry of Object.values(archive.files)) {
    if (entry.dir || !entry.name.split(/[\\/]/).pop()) continue;
    files.push(createTestcaseFile(entry.name, await entry.async("uint8array")));
  }
  if (!files.length) throw new Error("The ZIP archive contains no files.");
  return files;
}
