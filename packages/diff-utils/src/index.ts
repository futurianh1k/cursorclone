/**
 * Minimal Diff Utils (PoC)
 * TODO(Task C): Implement:
 * - parseUnifiedDiff
 * - validatePatch (no ../, size limits, allowlist)
 * - applyPatchToText
 */
export type PatchValidationResult = { valid: boolean; reason?: string; files?: string[] };

export function validatePatch(patch: string): PatchValidationResult {
  if (!patch || patch.length < 10) return { valid: false, reason: "empty_or_too_small" };
  if (patch.includes("..")) return { valid: false, reason: "path_traversal_suspected" };
  return { valid: true, files: [] };
}
