import React, { useState, useEffect } from "react";
import axios from "axios";
import DiffViewer from "react-diff-viewer";

export default function AskAnythingPage() {
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [diffs, setDiffs] = useState([]);
  const [uploadFiles, setUploadFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingCommit, setLoadingCommit] = useState(false);
  const [loadingAsk, setLoadingAsk] = useState(false);
  const [error, setError] = useState("");
  const [commitMessage, setCommitMessage] = useState("");

  const fetchFiles = async () => {
    setLoadingFiles(true);
    setError("");
    try {
      const res = await axios.post("/github/tree", {}, { withCredentials: true });
      setFiles(res.data.files || []);
      setSelectedFiles(new Set());
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch files");
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const toggleFileSelection = (path) => {
    const newSet = new Set(selectedFiles);
    if (newSet.has(path)) {
      newSet.delete(path);
    } else {
      newSet.add(path);
    }
    setSelectedFiles(newSet);
  };

  const handleFileUploadChange = (e) => {
    setUploadFiles(Array.from(e.target.files));
  };

  const handleAsk = async () => {
    setLoadingAsk(true);
    setError("");
    setDiffs([]);
    try {
      const formData = new FormData();
      formData.append("prompt", prompt);
      uploadFiles.forEach((file) => {
        formData.append("uploaded_files", file);
      });

      const res = await axios.post("/ask", formData, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });

      setDiffs(res.data.diffs || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to get response from Ask API");
    } finally {
      setLoadingAsk(false);
    }
  };

  const handleCommit = async () => {
    if (selectedFiles.size === 0) {
      setError("Select at least one file to commit.");
      return;
    }
    if (!commitMessage.trim()) {
      setError("Commit message is required.");
      return;
    }
    setLoadingCommit(true);
    setError("");
    try {
      // For each selected file, fetch content from backend
      const filesToCommit = [];
      for (const path of selectedFiles) {
        const res = await axios.post(
          "/github/file",
          { path },
          { withCredentials: true }
        );
        const diff = diffs.find((d) => d.path === path);
        let content = res.data.content;
        // If diff new content exists, use it
        if (diff && diff.new !== undefined && diff.new !== null) {
          content = diff.new;
        }
        filesToCommit.push({ path, content });
      }

      await axios.post(
        "/github/commit",
        {
          message: commitMessage,
          files: filesToCommit,
        },
        { withCredentials: true }
      );

      setCommitMessage("");
      setSelectedFiles(new Set());
      setDiffs([]);
      fetchFiles();
      alert("Commit successful");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to commit changes");
    } finally {
      setLoadingCommit(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Ask Anything</h2>

      <div className="mb-4">
        <label className="block mb-1">Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          className="w-full border border-gray-300 rounded p-2"
          placeholder="Enter your prompt here"
        />
      </div>

      <div className="mb-4">
        <label className="block mb-1">Upload Files (optional)</label>
        <input type="file" multiple onChange={handleFileUploadChange} />
      </div>

      <div className="mb-4">
        <button
          onClick={handleAsk}
          disabled={loadingAsk || !prompt.trim()}
          className={`px-4 py-2 rounded text-white ${loadingAsk || !prompt.trim() ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"}`}
        >
          {loadingAsk ? "Asking..." : "Ask"}
        </button>
      </div>

      <div className="mb-4">
        <h3 className="text-xl font-semibold mb-2">Repository Files</h3>
        <button
          onClick={fetchFiles}
          disabled={loadingFiles}
          className={`mb-2 px-3 py-1 rounded text-white ${loadingFiles ? "bg-gray-400" : "bg-green-600 hover:bg-green-700"}`}
        >
          {loadingFiles ? "Refreshing..." : "Refresh File List"}
        </button>
        {files.length === 0 && <div>No files found in repository.</div>}
        <ul className="max-h-48 overflow-auto border border-gray-300 rounded p-2">
          {files.map((file) => (
            <li key={file} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={selectedFiles.has(file)}
                onChange={() => toggleFileSelection(file)}
              />
              <span>{file}</span>
            </li>
          ))}
        </ul>
      </div>

      {diffs.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xl font-semibold mb-2">Diff Viewer</h3>
          <div className="space-y-6 max-h-96 overflow-auto border border-gray-300 rounded p-2">
            {diffs.map(({ path, old, new: newContent }) => (
              <div key={path}>
                <h4 className="font-semibold mb-1">{path}</h4>
                <DiffViewer
                  oldValue={old || ""}
                  newValue={newContent || ""}
                  splitView={true}
                  hideLineNumbers={false}
                  showDiffOnly={false}
                  styles={{
                    variables: {
                      light: {
                        diffViewerBackground: '#f6f8fa',
                        addedBackground: '#e6ffed',
                        addedGutterBackground: '#cdffd8',
                        removedBackground: '#ffeef0',
                        removedGutterBackground: '#ffdce0',
                      },
                    },
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4">
        <label className="block mb-1">Commit Message</label>
        <input
          type="text"
          value={commitMessage}
          onChange={(e) => setCommitMessage(e.target.value)}
          className="w-full border border-gray-300 rounded p-2"
          placeholder="Enter commit message"
        />
      </div>

      <div>
        <button
          onClick={handleCommit}
          disabled={loadingCommit || selectedFiles.size === 0 || !commitMessage.trim()}
          className={`px-4 py-2 rounded text-white ${loadingCommit || selectedFiles.size === 0 || !commitMessage.trim() ? "bg-gray-400" : "bg-purple-600 hover:bg-purple-700"}`}
        >
          {loadingCommit ? "Committing..." : "Commit Selected Changes"}
        </button>
      </div>

      {error && <div className="text-red-600 mt-4">{error}</div>}
    </div>
  );
}
