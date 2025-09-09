# demorepo

## GitHub Integration Backend with Authentication and OpenAI Integration

This backend provides API endpoints to interact with GitHub repositories using personal access tokens.
It also supports user authentication with JWT tokens, refresh token rotation, and secure cookie storage.
Additionally, it supports storing per-user OpenAI API keys encrypted and an "Ask Anything" flow that fetches repo files, sends prompts and attachments to OpenAI, and returns JSON diffs.

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
- "Ask Anything" API that sends repo files, user prompt, and optional uploaded files (converted to low-res base64 images) to OpenAI API and returns JSON diffs.

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

7. To start the frontend UI locally:

```bash
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173` (default Vite port).

**Note:** The backend requires the `python-multipart` package to handle form data. This is installed automatically by the setup script and included in the Docker image.

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
- `POST /ask` - Ask Anything flow: send repo files, prompt, and optional uploaded files to OpenAI, get JSON diffs.

### Docker Compose

Use the provided `docker-compose.yml` to run the backend with a single command.

```bash
docker-compose up --build
```

The backend will be available on port 8000.

### Shell Scripts

- `setup_prerequisites.sh`: Installs Python dependencies and checks local environment.
- `init_db.sh`: Initializes the database schema.
- `start_backend.sh`: Starts the backend server locally.

### Frontend

The frontend is built with React, Vite, Tailwind CSS, and Axios.

Run `npm install` and `npm run dev` in the `frontend` directory to start the UI locally.

### Docker Compose for External/Cloud Deployment

The `docker-compose.yml` includes services for backend, PostgreSQL, and Redis.

Run `docker-compose up --build` to start all services.

The backend will be accessible on port 8000.

You can configure environment variables in the `docker-compose.yml` as needed.
