"use client";

import { useState, useRef, useCallback } from "react";
import { uploadFiles, uploadZip, UploadResult, ZipUploadResult } from "@/lib/api";

interface FileUploadPanelProps {
  workspaceId: string;
  currentPath?: string;
  onUploadComplete?: () => void;
}

export default function FileUploadPanel({
  workspaceId,
  currentPath = "",
  onUploadComplete,
}: FileUploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | ZipUploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [targetDir, setTargetDir] = useState(currentPath);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleUpload(files);
    }
  }, [workspaceId, targetDir, overwrite]);

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    setUploading(true);
    setError(null);
    setUploadResult(null);
    
    try {
      // ZIP 파일인 경우
      if (files.length === 1 && files[0].name.toLowerCase().endsWith(".zip")) {
        const result = await uploadZip(workspaceId, files[0], targetDir, overwrite);
        setUploadResult(result);
      } else {
        // 일반 파일 업로드
        const result = await uploadFiles(workspaceId, files, targetDir, overwrite);
        setUploadResult(result);
      }
      
      onUploadComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleUpload(files);
    }
    // 입력 초기화 (같은 파일 다시 선택 가능하게)
    e.target.value = "";
  };

  const handleZipSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0 && files[0].name.toLowerCase().endsWith(".zip")) {
      handleUpload([files[0]]);
    }
    e.target.value = "";
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div style={{ padding: "16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h3 style={{ margin: "0 0 16px", fontSize: "18px" }}>
        📤 파일 업로드
      </h3>

      {/* 옵션 */}
      <div style={{ marginBottom: "16px", display: "flex", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <label style={{ fontSize: "12px", color: "#666", display: "block", marginBottom: "4px" }}>
            대상 디렉토리
          </label>
          <input
            type="text"
            value={targetDir}
            onChange={(e) => setTargetDir(e.target.value)}
            placeholder="/ (루트)"
            style={{
              padding: "8px 12px",
              fontSize: "13px",
              border: "1px solid #ddd",
              borderRadius: "6px",
              width: "200px",
            }}
          />
        </div>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={overwrite}
              onChange={(e) => setOverwrite(e.target.checked)}
            />
            <span style={{ fontSize: "13px" }}>기존 파일 덮어쓰기</span>
          </label>
        </div>
      </div>

      {/* 드래그 앤 드롭 영역 */}
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${isDragging ? "#007acc" : "#ddd"}`,
          borderRadius: "12px",
          padding: "40px 20px",
          textAlign: "center",
          backgroundColor: isDragging ? "#e3f2fd" : "#fafafa",
          transition: "all 0.2s",
          cursor: "pointer",
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? (
          <div>
            <div style={{ fontSize: "32px", marginBottom: "12px" }}>⏳</div>
            <div style={{ fontSize: "14px", color: "#666" }}>업로드 중...</div>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: "48px", marginBottom: "12px" }}>
              {isDragging ? "📥" : "📁"}
            </div>
            <div style={{ fontSize: "14px", color: "#333", marginBottom: "8px" }}>
              파일을 여기에 드래그하거나 클릭하여 선택
            </div>
            <div style={{ fontSize: "12px", color: "#888" }}>
              단일/다중 파일 또는 ZIP 아카이브 지원
            </div>
          </div>
        )}
      </div>

      {/* 숨겨진 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />
      <input
        ref={zipInputRef}
        type="file"
        accept=".zip"
        onChange={handleZipSelect}
        style={{ display: "none" }}
      />

      {/* 버튼 그룹 */}
      <div style={{ marginTop: "16px", display: "flex", gap: "8px" }}>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          style={{
            padding: "10px 20px",
            fontSize: "13px",
            backgroundColor: uploading ? "#ccc" : "#007acc",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: uploading ? "not-allowed" : "pointer",
          }}
        >
          📄 파일 선택
        </button>
        <button
          onClick={() => zipInputRef.current?.click()}
          disabled={uploading}
          style={{
            padding: "10px 20px",
            fontSize: "13px",
            backgroundColor: uploading ? "#ccc" : "#7c3aed",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: uploading ? "not-allowed" : "pointer",
          }}
        >
          📦 ZIP 업로드
        </button>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div style={{
          marginTop: "16px",
          padding: "12px",
          backgroundColor: "#ffebee",
          color: "#c62828",
          borderRadius: "8px",
          fontSize: "13px",
        }}>
          ❌ {error}
        </div>
      )}

      {/* 업로드 결과 */}
      {uploadResult && (
        <div style={{
          marginTop: "16px",
          padding: "12px",
          backgroundColor: uploadResult.success ? "#e8f5e9" : "#fff3cd",
          borderRadius: "8px",
          fontSize: "13px",
        }}>
          <div style={{ fontWeight: 500, marginBottom: "8px" }}>
            {"extractedFiles" in uploadResult
              ? `📦 ZIP 압축 해제 완료 (${uploadResult.totalExtracted}개 파일)`
              : `📤 업로드 완료 (${uploadResult.totalUploaded}개 파일)`}
          </div>
          
          {/* 업로드된 파일 목록 */}
          {"uploadedFiles" in uploadResult && uploadResult.uploadedFiles.length > 0 && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>업로드된 파일:</div>
              <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px" }}>
                {uploadResult.uploadedFiles.slice(0, 10).map((f, i) => (
                  <li key={i}>
                    {f.path} <span style={{ color: "#888" }}>({formatSize(f.size)})</span>
                  </li>
                ))}
                {uploadResult.uploadedFiles.length > 10 && (
                  <li style={{ color: "#888" }}>...외 {uploadResult.uploadedFiles.length - 10}개</li>
                )}
              </ul>
            </div>
          )}
          
          {"extractedFiles" in uploadResult && uploadResult.extractedFiles.length > 0 && (
            <div style={{ marginTop: "8px" }}>
              <div style={{ fontSize: "11px", color: "#666", marginBottom: "4px" }}>압축 해제된 파일:</div>
              <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px" }}>
                {uploadResult.extractedFiles.slice(0, 10).map((f, i) => (
                  <li key={i}>
                    {f.path} <span style={{ color: "#888" }}>({formatSize(f.size)})</span>
                  </li>
                ))}
                {uploadResult.extractedFiles.length > 10 && (
                  <li style={{ color: "#888" }}>...외 {uploadResult.extractedFiles.length - 10}개</li>
                )}
              </ul>
            </div>
          )}
          
          {/* 에러 목록 */}
          {uploadResult.errors.length > 0 && (
            <div style={{ marginTop: "8px", color: "#c62828" }}>
              <div style={{ fontSize: "11px", marginBottom: "4px" }}>⚠️ 오류:</div>
              <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12px" }}>
                {uploadResult.errors.map((e, i) => (
                  <li key={i}>{e.file}: {e.error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 안내 */}
      <div style={{
        marginTop: "20px",
        padding: "12px",
        backgroundColor: "#f5f5f5",
        borderRadius: "8px",
        fontSize: "12px",
        color: "#666",
      }}>
        <strong>💡 금융권 폐쇄망 환경 안내:</strong>
        <ul style={{ margin: "8px 0 0", paddingLeft: "20px" }}>
          <li>GitHub 접속이 불가능한 경우, 이 기능으로 소스코드를 업로드하세요.</li>
          <li>node_modules, vendor 등 패키지는 ZIP으로 압축하여 업로드할 수 있습니다.</li>
          <li>SSH 접속 시 SCP/SFTP를 사용할 수도 있습니다.</li>
        </ul>
      </div>
    </div>
  );
}
