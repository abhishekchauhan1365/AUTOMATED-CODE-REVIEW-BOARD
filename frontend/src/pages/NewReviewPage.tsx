import { useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileCode2,
  GitCompare,
  Play,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import { createDiffReview, createFilesReview } from "../services/api";

const ACCEPTED_EXTENSIONS = [
  ".py",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".java",
  ".cpp",
  ".c",
  ".go",
];

const SAMPLE_VULNERABLE_DIFF = `diff --git a/api/auth_handler.py b/api/auth_handler.py
new file mode 100644
--- /dev/null
+++ b/api/auth_handler.py
@@ -0,0 +1,19 @@
+import sqlite3
+import subprocess
+
+GROQ_API_SECRET = "gsk_9876543210abcdefghijklmnop"
+
+def fetch_user_profile(conn, username):
+    cursor = conn.cursor()
+    cursor.execute(f"SELECT id, email FROM users WHERE username = '{username}'")
+    return cursor.fetchone()
+
+def evaluate_filter(expr):
+    return eval(expr)
+
+def run_diagnostics(host):
+    subprocess.run(f"ping -c 1 {host}", shell=True)
`;

const SAMPLE_CLEAN_FILES = [
  {
    path: "calculator.py",
    content: `"""Safe arithmetic module."""


def divide_numbers(numerator: float, denominator: float) -> float:
    """Divide numerator by denominator safely."""
    if denominator == 0:
        raise ValueError("Denominator cannot be zero.")
    return round(numerator / denominator, 4)
`,
  },
  {
    path: "test_calculator.py",
    content: `"""Unit tests for calculator module."""

import pytest
from calculator import divide_numbers


def test_divide_numbers_valid():
    assert divide_numbers(10.0, 2.0) == 5.0


def test_divide_numbers_zero_raises():
    with pytest.raises(ValueError):
        divide_numbers(10.0, 0.0)
`,
  },
];

interface UploadedItem {
  path: string;
  content: string;
  size: number;
}

export function NewReviewPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"diff" | "files">("diff");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [gitDiff, setGitDiff] = useState(SAMPLE_VULNERABLE_DIFF);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedItem[]>([]);
  const [demoMode, setDemoMode] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileInput = async (e: ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList) return;
    setError(null);

    const nextItems: UploadedItem[] = [];
    for (const file of Array.from(fileList)) {
      const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        setError(
          `Unsupported file '${file.name}'. Allowed: ${ACCEPTED_EXTENSIONS.join(", ")}`
        );
        continue;
      }
      const text = await file.text();
      nextItems.push({ path: file.name, content: text, size: file.size });
    }
    setUploadedFiles((prev) => {
      const existingNames = new Set(prev.map((p) => p.path));
      const deduped = nextItems.filter((n) => !existingNames.has(n.path));
      return [...prev, ...deduped];
    });
    e.target.value = "";
  };

  const removeFile = (path: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.path !== path));
  };

  const loadCleanSample = () => {
    setMode("files");
    setTitle("Clean Division Helper PR");
    setDescription("Adds divide_numbers utility along with unit tests.");
    setUploadedFiles(
      SAMPLE_CLEAN_FILES.map((f) => ({
        path: f.path,
        content: f.content,
        size: f.content.length,
      }))
    );
    setError(null);
  };

  const loadVulnerableSample = () => {
    setMode("diff");
    setTitle("Auth Handler & Diagnostics Patch");
    setDescription("Sample PR containing hardcoded secret, SQLi, eval, and shell=True.");
    setGitDiff(SAMPLE_VULNERABLE_DIFF);
    setError(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created =
        mode === "diff"
          ? await createDiffReview({
              title: title.trim() || undefined,
              description,
              git_diff: gitDiff,
              demo_mode: demoMode,
            })
          : await createFilesReview({
              title: title.trim() || undefined,
              description,
              files: uploadedFiles.map((f) => ({ path: f.path, content: f.content })),
              demo_mode: demoMode,
            });
      navigate(`/reviews/${created.review_id}/live`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start code review");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Submit Code for Review</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Upload source files or paste a unified Git diff to trigger the 6-agent Semantic Kernel pipeline.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadVulnerableSample}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-surface-700 bg-surface-900 hover:bg-surface-800 text-xs text-slate-300"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Vulnerable Diff Sample
          </button>
          <button
            type="button"
            onClick={loadCleanSample}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-surface-700 bg-surface-900 hover:bg-surface-800 text-xs text-slate-300"
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            Clean Files Sample
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Review Title (optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Auth service refactor"
              className="w-full rounded-md bg-surface-900 border border-surface-700 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              LLM Execution Mode
            </label>
            <label className="flex items-center justify-between rounded-md bg-surface-900 border border-surface-700 px-3 py-2 cursor-pointer">
              <span className="text-xs text-slate-300">
                Deterministic Demo Mode (no Groq key required)
              </span>
              <input
                type="checkbox"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
                className="accent-blue-500 w-4 h-4"
              />
            </label>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Review Description (optional)
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this PR or change is supposed to implement..."
            className="w-full rounded-md bg-surface-900 border border-surface-700 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
          <div className="flex border-b border-surface-700 bg-surface-950/60">
            <button
              type="button"
              onClick={() => setMode("diff")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                mode === "diff"
                  ? "border-blue-500 text-slate-100 bg-surface-900"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <GitCompare className="w-4 h-4" />
              Paste Git Diff
            </button>
            <button
              type="button"
              onClick={() => setMode("files")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                mode === "files"
                  ? "border-blue-500 text-slate-100 bg-surface-900"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload Source Files ({uploadedFiles.length})
            </button>
          </div>

          {mode === "diff" ? (
            <div className="p-4 space-y-2">
              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>Unified Git Diff Editor</span>
                <span>{gitDiff.split("\n").length} lines</span>
              </div>
              <textarea
                value={gitDiff}
                onChange={(e) => setGitDiff(e.target.value)}
                rows={15}
                spellCheck={false}
                placeholder="Paste unified git diff (diff --git a/... b/...) here..."
                className="w-full rounded-md bg-surface-850 border border-surface-700 p-3 font-mono text-xs text-slate-100 leading-relaxed focus:outline-none focus:border-blue-500"
              />
            </div>
          ) : (
            <div className="p-5 space-y-4">
              <label className="flex flex-col items-center justify-center rounded-lg border border-dashed border-surface-700 hover:border-blue-500/60 bg-surface-950/60 p-6 cursor-pointer transition-colors">
                <Upload className="w-6 h-6 text-slate-400 mb-2" />
                <span className="text-sm font-medium text-slate-200">
                  Click to select source or test files
                </span>
                <span className="text-xs text-slate-400 mt-1 font-mono">
                  Supports: {ACCEPTED_EXTENSIONS.join(" ")}
                </span>
                <input
                  type="file"
                  multiple
                  accept={ACCEPTED_EXTENSIONS.join(",")}
                  onChange={handleFileInput}
                  className="hidden"
                />
              </label>

              {uploadedFiles.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-slate-300">
                    Queued Files ({uploadedFiles.length})
                  </div>
                  <div className="divide-y divide-surface-700 rounded-md border border-surface-700 bg-surface-950">
                    {uploadedFiles.map((file) => (
                      <div
                        key={file.path}
                        className="px-3 py-2 flex items-center justify-between gap-3"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <FileCode2 className="w-4 h-4 text-blue-400 shrink-0" />
                          <span className="text-xs font-mono text-slate-200 truncate">
                            {file.path}
                          </span>
                          <span className="text-[11px] font-mono text-slate-500">
                            ({file.size} bytes)
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeFile(file.path)}
                          className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-surface-800"
                          title="Remove file"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-md bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-300">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            disabled={
              submitting ||
              (mode === "diff" ? !gitDiff.trim() : uploadedFiles.length === 0)
            }
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors"
          >
            <Play className="w-4 h-4" />
            {submitting ? "Dispatching Agents..." : "Start Review"}
          </button>
        </div>
      </form>
    </div>
  );
}

