# demorepo

## GitHub Integration Backend with Authentication

This backend provides API endpoints to interact with GitHub repositories using personal access tokens.
It also supports user authentication with JWT tokens, refresh token rotation, and secure cookie storage.

### Features

- User signup and login with email and password (hashed using bcrypt).
- JWT authentication with access and refresh tokens.
- Refresh token rotation and secure HttpOnly cookies.
- Store GitHub username, repository name, GitHub personal access token, and OpenAI API token per user.
- Fetch repository contents recursively using GitHub tree API.
- Get file content decoded from base64.
- Commit changes flow implemented (create blobs -> tree -> commit -> update ref).
- Works even if the repository is empty (creates first commit and branch ref).
- Default branch detection with fallback from `main` to `master`.
- Graceful handling of empty repositories when listing files.

### Local Deployment

1. Ensure you have Python 3.9+ installed.
2. Ensure you have PostgreSQL installed and running locally.
3. Run the setup script to install dependencies and check prerequisites:

```bash
./setup_prerequisites.sh
```

4. Initialize the database schema:

```bash
./init_db.sh
```

5. Start the backend server:

```bash
./start_backend.sh
```

6. The API will be available at `http://localhost:8000`.

### API Endpoints

- `POST /signup` - Register a new user.
- `POST /login` - Login and receive access and refresh tokens in secure cookies.
- `POST /logout` - Logout and clear tokens.
- `POST /refresh` - Refresh access token using refresh token cookie.
- `GET /user/github-config` - Get stored GitHub and OpenAI tokens.
- `POST /user/github-config` - Update GitHub and OpenAI tokens.
- `POST /github/tree` - Get recursive tree of repo files (requires auth).
- `POST /github/file` - Get file content (requires auth).
- `POST /github/commit` - Commit changes (requires auth).

### Docker Compose

Use the provided `docker-compose.yml` to run the backend with a single command.

```bash
docker-compose up --build
```

The backend will be available on port 8000.
