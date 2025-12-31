/**
 * Diff Utils 테스트
 * Task C: Diff 유틸 구현 테스트
 * 
 * TODO: vitest 설정 후 실행
 * pnpm add -D vitest @types/node -w
 */

import {
  parseUnifiedDiff,
  validatePatch,
  applyPatchToText,
  ALLOWED_EXTENSIONS,
  MAX_PATCH_SIZE,
} from "./index";

describe("parseUnifiedDiff", () => {
  it("should parse simple unified diff", () => {
    const patch = `--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,1 @@
-old
+new
`;
    
    const result = parseUnifiedDiff(patch);
    expect(result).toHaveLength(1);
    expect(result[0].oldPath).toBe("src/main.py");
    expect(result[0].newPath).toBe("src/main.py");
    expect(result[0].hunks).toHaveLength(1);
  });
  
  it("should parse multi-file diff", () => {
    const patch = `--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-old1
+new1
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-old2
+new2
`;
    
    const result = parseUnifiedDiff(patch);
    expect(result).toHaveLength(2);
  });
});

describe("validatePatch", () => {
  it("should reject empty patch", () => {
    const result = validatePatch("");
    expect(result.valid).toBe(false);
    expect(result.reason).toBe("empty_or_too_small");
  });
  
  it("should reject path traversal", () => {
    const patch = `--- a/../etc/passwd
+++ b/../etc/passwd
@@ -1,1 +1,1 @@
-old
+new
`;
    
    const result = validatePatch(patch);
    expect(result.valid).toBe(false);
    expect(result.reason).toBe("path_traversal_suspected");
  });
  
  it("should reject disallowed extension", () => {
    const patch = `--- a/file.exe
+++ b/file.exe
@@ -1,1 +1,1 @@
-old
+new
`;
    
    const result = validatePatch(patch);
    expect(result.valid).toBe(false);
    expect(result.reason).toBe("extension_not_allowed");
  });
  
  it("should accept valid patch", () => {
    const patch = `--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,1 @@
-old
+new
`;
    
    const result = validatePatch(patch);
    expect(result.valid).toBe(true);
    expect(result.files).toContain("src/main.py");
  });
});

describe("applyPatchToText", () => {
  it("should apply simple patch", () => {
    const original = "old\nline2";
    const patch = `--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old
+new
`;
    
    const result = applyPatchToText(original, patch);
    expect(result.success).toBe(true);
    expect(result.content).toBe("new\nline2");
    expect(result.appliedHunks).toBe(1);
  });
  
  it("should detect context mismatch", () => {
    const original = "different\nline2";
    const patch = `--- a/file.py
+++ b/file.py
@@ -1,1 +1,1 @@
-old
+new
`;
    
    const result = applyPatchToText(original, patch);
    expect(result.success).toBe(false);
    expect(result.conflicts).toBeDefined();
  });
});

// 간단한 실행 테스트 (vitest 없이)
if (require.main === module) {
  console.log("Running basic tests...");
  
  // parseUnifiedDiff 테스트
  const patch = `--- a/src/main.py
+++ b/src/main.py
@@ -1,1 +1,1 @@
-old
+new
`;
  
  try {
    const parsed = parseUnifiedDiff(patch);
    console.log("✅ parseUnifiedDiff: PASS");
    console.log(`   Files: ${parsed.length}`);
  } catch (error) {
    console.log("❌ parseUnifiedDiff: FAIL", error);
  }
  
  // validatePatch 테스트
  const validation = validatePatch(patch);
  if (validation.valid) {
    console.log("✅ validatePatch: PASS");
  } else {
    console.log("❌ validatePatch: FAIL", validation.reason);
  }
  
  // applyPatchToText 테스트
  const original = "old\nline2";
  const applyResult = applyPatchToText(original, patch);
  if (applyResult.success && applyResult.content === "new\nline2") {
    console.log("✅ applyPatchToText: PASS");
  } else {
    console.log("❌ applyPatchToText: FAIL", applyResult);
  }
}
