-- Initial schema. Applied once by app/db.py under an advisory lock.

-- Workspace members this app has seen (upserted from verified tokens).
-- Used for assignee/role pickers; never a source of identity.
create table users (
  id            text primary key,
  email         text,
  name          text,
  first_seen_at timestamptz not null default now(),
  last_seen_at  timestamptz not null default now()
);
create index users_email_idx on users (lower(email));

-- App-level roles granted by admins. Keyed by user id (stable), email kept for display.
-- Admins themselves are configured at deploy time (ADMIN_EMAILS / platform role claim).
create table app_roles (
  user_id    text primary key references users(id) on delete cascade,
  role       text not null check (role in ('triager')),
  granted_by text not null,
  granted_at timestamptz not null default now()
);

create table tickets (
  id                 uuid primary key default gen_random_uuid(),
  number             bigint generated always as identity unique,
  title              text not null check (char_length(title) between 3 and 120),
  description        text not null default '' check (char_length(description) <= 10000),
  steps_to_reproduce text check (char_length(steps_to_reproduce) <= 5000),
  expected_behavior  text check (char_length(expected_behavior) <= 2000),
  actual_behavior    text check (char_length(actual_behavior) <= 2000),
  environment        text check (char_length(environment) <= 500),
  severity           text not null default 'medium' check (severity in ('low','medium','high','critical')),
  status             text not null default 'open' check (status in ('open','in_progress','resolved','closed')),
  target_app         text not null check (char_length(target_app) between 1 and 80),
  -- Confidential tickets (e.g. security issues) are visible to the reporter and triagers only.
  confidential       boolean not null default false,

  -- Identity is always taken from the verified token, never from request bodies.
  reporter_id        text not null,
  reporter_email     text,
  reporter_name      text,
  created_via        text not null check (created_via in ('ui','agent')),
  created_by_agent   text,

  assignee_id        text,
  assignee_email     text,
  assignee_name      text,

  -- Idempotency: unique per reporter. request_hash detects key reuse with a different payload.
  request_key        text,
  request_hash       text,

  version            integer not null default 1,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  resolved_at        timestamptz
);

create unique index tickets_reporter_request_key_uq on tickets (reporter_id, request_key)
  where request_key is not null;
create index tickets_status_idx     on tickets (status, number desc);
create index tickets_reporter_idx   on tickets (reporter_id, number desc);
create index tickets_assignee_idx   on tickets (assignee_id, number desc);
create index tickets_target_app_idx on tickets (lower(target_app), number desc);

-- Append-only activity log: audit trail + comments.
create table ticket_events (
  id          bigint generated always as identity primary key,
  ticket_id   uuid not null references tickets(id) on delete cascade,
  type        text not null check (type in ('created','updated','status_changed','assigned','comment')),
  actor_id    text not null,
  actor_name  text,
  actor_email text,
  actor_agent text,
  body        text check (char_length(body) <= 5000),
  data        jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index ticket_events_ticket_idx on ticket_events (ticket_id, id);
