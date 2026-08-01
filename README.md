# Blog API

FastAPI blog service with **Supabase Auth/users** and **Docker Postgres posts**, plus production-oriented cross-cutting concerns (validation, error envelopes, rate limiting, security headers).

## Architecture

| Data | Where |
|------|--------|
| Auth (signup/login/JWT) | Supabase Auth |
| User profiles (`username`, `email`) | Supabase `public.users` |
| Posts | Local Docker Postgres (`DATABASE_URL`) |

There is **no cross-database foreign key**. Local `posts.user_id` stores the Supabase Auth UUID; author details are loaded from Supabase when returning posts.

```
Client → FastAPI
          ├─ Supabase Auth + public.users
          └─ Docker Postgres (posts only)
```

## Features

- **Auth** — Supabase signup/login; Bearer tokens from Supabase; Swagger Authorize via `/auth/token`
- **Users** — register, get, update, delete (update/delete require owning the account)
- **Posts** — CRUD + search with pagination; create/update/delete require auth and ownership
- **API contract** — `{ success, message, data, meta }` / error envelopes
- **Ops** — SlowAPI rate limits, Helmet-style headers, CORS, Trusted Host, request IDs

## Project layout

```
app/
  api/routes/     # auth, users, posts, health
  schemas/        # Pydantic request/response models
  services/       # business logic
  db/             # Docker Postgres posts + Supabase client
  core/           # exceptions, responses, rate limit, security
  middleware/     # request ID
  config.py       # env-driven settings
docs/
  supabase_users.sql
main.py
```

## Setup

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Run [`docs/supabase_users.sql`](docs/supabase_users.sql) in the SQL Editor.
3. Copy **Project URL** and **service_role** key (Settings → API). Use the service role on the server only.

Disable email confirmation in Auth settings if you want signup to work immediately in development.

Registration uses the **Admin** Auth API (`email_confirm: true`) so confirmation emails are not sent and the free-tier email rate limit is avoided. Use a real domain (e.g. `@gmail.com`, not `@egmail.com`).

**Passwords are not stored in `public.users`.** Supabase Auth keeps them in `auth.users`. The `public.users` table only holds profile fields (`id`, `username`, `email`, timestamps).

### 2. App env

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://postgres:dev@localhost:5433/blog
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_SERVICE_ROLE_KEY
```

### 3. Posts database (Docker)

```bash
docker compose up db -d
```

If you previously had the old integer `users`/`posts` schema, reset the volume once:

```bash
docker compose down -v
docker compose up db -d
```

## Run

**Option A — Docker (API + Postgres for posts):**

```bash
docker compose up --build
```

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  

**Option B — Local uvicorn + Compose DB:**

```bash
docker compose up db -d
uvicorn main:app --reload
```

Inspect posts DB:

```bash
docker exec -it blogdb psql -U postgres -d blog
```

## Auth flow

1. Register: `POST /users/create` → Supabase Auth user + `public.users` row  
2. Login: `POST /auth/login` → Supabase `access_token`  
3. Send `Authorization: Bearer <token>` on protected routes  

Swagger **Authorize**: `POST /auth/token` (`username` = email).

User IDs are **UUIDs** (strings), not integers.

Deleting a user removes their Supabase Auth/profile row and cleans up their local posts.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/auth/login` | No | JSON login → Supabase JWT |
| POST | `/auth/token` | No | OAuth2 form login (Swagger) |
| POST | `/users/create` | No | Register user |
| GET | `/users/get/{user_id}` | No | Get user by UUID |
| PUT | `/users/update/{user_id}` | Yes (owner) | Update profile |
| DELETE | `/users/delete/{user_id}` | Yes (owner) | Delete profile + posts |
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
