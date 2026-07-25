# Blog API

FastAPI blog service with JWT auth, users, posts, PostgreSQL persistence, and production-oriented cross-cutting concerns (validation, error envelopes, rate limiting, security headers).

## Features

- **Auth** — bcrypt password hashing, JWT bearer tokens, Swagger Authorize via `/auth/token`
- **Users** — register, get, update, delete (update/delete require owning the account)
- **Posts** — CRUD + search with pagination; create/update/delete require auth and ownership
- **PostgreSQL** — `users` and `posts` tables via `psycopg3`; schema created on startup
- **API contract** — consistent `{ success, message, data, meta }` / error envelopes
- **Ops** — SlowAPI rate limits, Helmet-style headers, CORS, Trusted Host, request IDs, `.env` settings

## Project layout

```
app/
  api/routes/     # auth, users, posts, health
  schemas/        # Pydantic request/response models
  services/       # business logic
  db/             # PostgreSQL helpers
  core/           # exceptions, responses, rate limit, security
  utils/          # JWT + password helpers
  middleware/     # request ID
  config.py       # env-driven settings
main.py           # uvicorn entry (`main:app`)
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Default local DB URL (Compose maps Postgres to host port **5433**):

```env
DATABASE_URL=postgresql://postgres:dev@localhost:5433/blog
SECRET_KEY=dev-secret-change-me-in-production
```

Change `SECRET_KEY` before any real deployment.

## Run

### Option A — Docker (API + PostgreSQL)

```bash
docker compose up --build
```

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  

### Option B — Local uvicorn + Compose DB only

```bash
docker compose up db -d
uvicorn main:app --reload
```

- Docs: http://127.0.0.1:8000/docs  
- Health: `GET /health`

Inspect the database:

```bash
docker exec -it blogdb psql -U postgres -d blog
```

## Auth flow

1. Register: `POST /users/create`
2. Login: `POST /auth/login` with `{ "email", "password" }` → `access_token`
3. Send `Authorization: Bearer <token>` on protected routes

For Swagger **Authorize**, use `POST /auth/token` (`username` = email, `password` = password).

Protected:

| Action | Rule |
|--------|------|
| Create / update / delete post | Must be authenticated; update/delete only own posts |
| Update / delete user | Must be authenticated; only own profile |

Public: health, register, login, get user, list/get/search posts.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/auth/login` | No | JSON login → JWT |
| POST | `/auth/token` | No | OAuth2 form login (Swagger) |
| POST | `/users/create` | No | Register user |
| GET | `/users/get/{user_id}` | No | Get user by id |
| PUT | `/users/update/{user_id}` | Yes (owner) | Update profile |
| DELETE | `/users/delete/{user_id}` | Yes (owner) | Delete profile |
| POST | `/posts` | Yes | Create post |
| GET | `/posts` | No | List posts |
| GET | `/posts/search` | No | Search posts (paginated) |
| GET | `/posts/{post_id}` | No | Get post by id |
| PUT | `/posts/{post_id}` | Yes (owner) | Update post |
| DELETE | `/posts/{post_id}` | Yes (owner) | Delete post |

### Search

```bash
curl "http://127.0.0.1:8000/posts/search?q=fastapi&page=1&page_size=10"
```

Query params: `q` (title/description), `page` (≥1), `page_size` (1–100).

Response `data`: `items`, `total`, `page`, `page_size`, `total_pages`.

## Examples

**Register**

```bash
curl -X POST http://127.0.0.1:8000/users/create \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'
```

**Login**

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'
```

**Create post**

```bash
curl -X POST http://127.0.0.1:8000/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"title":"Hello","description":"First post"}'
```

## Response shape

Success:

```json
{
  "success": true,
  "message": "...",
  "data": {},
  "meta": { "version": "1.0.0", "request_id": "..." }
}
```

Error:

```json
{
  "success": false,
  "message": "...",
  "errors": [],
  "meta": { "version": "1.0.0", "request_id": "..." }
}
```

Common status codes: `201` create, `400`/`401`/`403`/`404`/`409`, `422` validation, `429` rate limit, `500` unexpected.
