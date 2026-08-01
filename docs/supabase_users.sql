-- Run in Supabase SQL Editor (users live in Supabase; posts stay in Docker Postgres).
-- Passwords are stored by Supabase Auth in auth.users — NOT in this table.

create table if not exists public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  username text not null unique,
  email text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.users enable row level security;

-- Service role bypasses RLS; these policies help if you ever use the anon key.
drop policy if exists "users_select_all" on public.users;
drop policy if exists "users_insert_all" on public.users;
drop policy if exists "users_update_all" on public.users;
drop policy if exists "users_delete_all" on public.users;

create policy "users_select_all" on public.users for select using (true);
create policy "users_insert_all" on public.users for insert with check (true);
create policy "users_update_all" on public.users for update using (true);
create policy "users_delete_all" on public.users for delete using (true);
