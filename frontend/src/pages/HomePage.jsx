import React, { useState, useEffect } from "react";
import axios from "axios";

export default function HomePage() {
  const [githubUsername, setGithubUsername] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [openaiToken, setOpenaiToken] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    axios
      .get("/user/github-config", { withCredentials: true })
      .then((res) => {
        setGithubUsername(res.data.github_username || "");
        setGithubRepo(res.data.github_repo || "");
        setGithubToken(res.data.github_token || "");
        setOpenaiToken(res.data.openai_token || "");
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await axios.post(
        "/user/github-config",
        {
          github_username: githubUsername,
          github_repo: githubRepo,
          github_token: githubToken,
          openai_token: openaiToken
        },
        { withCredentials: true }
      );
      setMessage("Configuration saved successfully.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save configuration.");
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-2xl font-bold mb-4">Configure GitHub and OpenAI Credentials</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-1">GitHub Username</label>
          <input
            type="text"
            value={githubUsername}
            onChange={(e) => setGithubUsername(e.target.value)}
            className="w-full border border-gray-300 rounded p-2"
            required
          />
        </div>
        <div>
          <label className="block mb-1">GitHub Repository Name</label>
          <input
            type="text"
            value={githubRepo}
            onChange={(e) => setGithubRepo(e.target.value)}
            className="w-full border border-gray-300 rounded p-2"
            required
          />
        </div>
        <div>
          <label className="block mb-1">GitHub Personal Access Token</label>
          <input
            type="password"
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
            className="w-full border border-gray-300 rounded p-2"
            required
          />
        </div>
        <div>
          <label className="block mb-1">OpenAI API Token</label>
          <input
            type="password"
            value={openaiToken}
            onChange={(e) => setOpenaiToken(e.target.value)}
            className="w-full border border-gray-300 rounded p-2"
            required
          />
        </div>
        {error && <div className="text-red-600">{error}</div>}
        {message && <div className="text-green-600">{message}</div>}
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Save Configuration
        </button>
      </form>
    </div>
  );
}
