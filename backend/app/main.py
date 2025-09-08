import base64
import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

GITHUB_API_URL = "https://api.github.com"

class GitHubConfig(BaseModel):
    username: str
    repo: str
    token: str

class FileContent(BaseModel):
    path: str
    content: str

class CommitRequest(BaseModel):
    message: str
    branch: Optional[str] = None
    files: List[FileContent]

async def get_default_branch(config: GitHubConfig):
    headers = {"Authorization": f"token {config.token}"}
    url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Repo not found or unauthorized")
        data = resp.json()
        default_branch = data.get("default_branch")
        if not default_branch:
            # fallback to main or master
            # check if main exists
            for branch in ["main", "master"]:
                branch_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/branches/{branch}"
                branch_resp = await client.get(branch_url, headers=headers)
                if branch_resp.status_code == 200:
                    return branch
            raise HTTPException(status_code=404, detail="No default branch found")
        return default_branch

@app.post("/github/tree")
async def get_repo_tree(config: GitHubConfig):
    """Fetch repo contents recursively"""
    headers = {"Authorization": f"token {config.token}"}
    default_branch = await get_default_branch(config)
    # get tree sha
    url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/trees/{default_branch}?recursive=1"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            # empty repo
            return {"files": []}
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch repo tree")
        data = resp.json()
        tree = data.get("tree", [])
        files = [item["path"] for item in tree if item["type"] == "blob"]
        return {"files": files}

@app.post("/github/file")
async def get_file_content(config: GitHubConfig, path: str):
    """Get file content decoded from base64"""
    headers = {"Authorization": f"token {config.token}"}
    url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/contents/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="File not found")
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch file content")
        data = resp.json()
        content_b64 = data.get("content", "")
        encoding = data.get("encoding", "")
        if encoding != "base64":
            raise HTTPException(status_code=500, detail="Unsupported encoding")
        content = base64.b64decode(content_b64).decode("utf-8")
        return {"path": path, "content": content}

@app.post("/github/commit")
async def commit_changes(config: GitHubConfig, commit_req: CommitRequest):
    """Commit changes flow: create blobs -> tree -> commit -> update ref"""
    headers = {"Authorization": f"token {config.token}"}
    async with httpx.AsyncClient() as client:
        # get default branch
        branch = commit_req.branch or await get_default_branch(config)

        # get ref
        ref_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/ref/heads/{branch}"
        ref_resp = await client.get(ref_url, headers=headers)
        if ref_resp.status_code == 404:
            # repo might be empty, no ref
            ref = None
        elif ref_resp.status_code != 200:
            raise HTTPException(status_code=ref_resp.status_code, detail="Failed to get ref")
        else:
            ref = ref_resp.json()

        # get base tree sha
        if ref:
            base_tree_sha = ref["object"]["sha"]
        else:
            base_tree_sha = None

        # create blobs for each file
        blobs = []
        for file in commit_req.files:
            blob_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/blobs"
            blob_data = {
                "content": file.content,
                "encoding": "utf-8"
            }
            blob_resp = await client.post(blob_url, headers=headers, json=blob_data)
            if blob_resp.status_code != 201:
                raise HTTPException(status_code=blob_resp.status_code, detail="Failed to create blob")
            blob_sha = blob_resp.json()["sha"]
            blobs.append({"path": file.path, "mode": "100644", "type": "blob", "sha": blob_sha})

        # create tree
        tree_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/trees"
        tree_data = {
            "tree": blobs
        }
        if base_tree_sha:
            tree_data["base_tree"] = base_tree_sha
        tree_resp = await client.post(tree_url, headers=headers, json=tree_data)
        if tree_resp.status_code != 201:
            raise HTTPException(status_code=tree_resp.status_code, detail="Failed to create tree")
        tree_sha = tree_resp.json()["sha"]

        # create commit
        commit_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/commits"
        parents = []
        if ref:
            parents.append(ref["object"]["sha"])
        commit_data = {
            "message": commit_req.message,
            "tree": tree_sha,
            "parents": parents
        }
        commit_resp = await client.post(commit_url, headers=headers, json=commit_data)
        if commit_resp.status_code != 201:
            raise HTTPException(status_code=commit_resp.status_code, detail="Failed to create commit")
        commit_sha = commit_resp.json()["sha"]

        # update ref
        if ref:
            update_ref_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/refs/heads/{branch}"
            update_data = {"sha": commit_sha}
            update_resp = await client.patch(update_ref_url, headers=headers, json=update_data)
            if update_resp.status_code != 200:
                raise HTTPException(status_code=update_resp.status_code, detail="Failed to update ref")
        else:
            # create ref (first commit)
            create_ref_url = f"{GITHUB_API_URL}/repos/{config.username}/{config.repo}/git/refs"
            create_data = {"ref": f"refs/heads/{branch}", "sha": commit_sha}
            create_resp = await client.post(create_ref_url, headers=headers, json=create_data)
            if create_resp.status_code != 201:
                raise HTTPException(status_code=create_resp.status_code, detail="Failed to create ref")

        return {"commit_sha": commit_sha}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
