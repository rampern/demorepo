# demorepo

## GitHub Integration Backend

This backend provides API endpoints to interact with GitHub repositories using personal access tokens.

### Features

- Store GitHub username, repository name, and personal access token.
- Fetch repository contents recursively using GitHub tree API.
- Get file content decoded from base64.
- Commit changes flow implemented (create blobs -> tree -> commit -> update ref).
- Works even if the repository is empty (creates first commit and branch ref).
- Default branch detection with fallback from `main` to `master`.
- Graceful handling of empty repositories when listing files.

### Local Deployment

1. Ensure you have Python 3.9+ installed.
2. Install dependencies:

```bash
pip install fastapi uvicorn httpx
```

3. Run the backend:

```bash
uvicorn backend.app.main:app --reload
```

4. The API will be available at `http://localhost:8000`.

### API Endpoints

- `POST /github/tree` - Get recursive tree of repo files.
- `POST /github/file` - Get file content.
- `POST /github/commit` - Commit changes.

### Docker Compose

Use the provided `docker-compose.yml` to run the backend with a single command.

```bash
docker-compose up --build
```

The backend will be available on port 8000.
