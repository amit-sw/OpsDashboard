-- ===============================
-- 0) SCHEMA & BASIC GRANTS
-- ===============================
-- Let API roles see the opsdashboard schema
grant usage on schema opsdashboard to anon, authenticated;

-- ===============================
-- 1) TABLES (BASE, IN opsdashboard)
-- ===============================
create table if not exists opsdashboard.gmail_message_index (
  id          text primary key,          -- Gmail message id
  thread_id   text,
  internal_ms bigint not null,           -- Gmail internalDate (milliseconds since epoch)
  ymd         date not null,             -- UTC date bucket
  created_at  timestamptz not null default now()
);

create table if not exists opsdashboard.gmail_messages (
  id          text primary key,          -- Gmail message id
  thread_id   text,
  internal_ms bigint,
  headers     jsonb,
  snippet     text,
  body_full   text,
  raw_json    jsonb,
  updated_at  timestamptz not null default now()
);

-- Helpful indexes
create index if not exists gmail_message_index_ymd_idx
  on opsdashboard.gmail_message_index (ymd);
create index if not exists gmail_message_index_internal_ms_idx
  on opsdashboard.gmail_message_index (internal_ms);

-- ===============================
-- 2) GRANTS ON BASE TABLES
-- (Postgres privileges are separate from RLS)
-- ===============================
grant select, insert, update
  on opsdashboard.gmail_message_index
  to anon, authenticated;

grant select, insert, update
  on opsdashboard.gmail_messages
  to anon, authenticated;

-- ===============================
-- 3) ROW LEVEL SECURITY (RLS)
-- Enable and add permissive policies (adjust as needed)
-- ===============================
alter table opsdashboard.gmail_message_index enable row level security;
alter table opsdashboard.gmail_messages     enable row level security;

-- SELECT policies
create policy if not exists gmi_select_all
  on opsdashboard.gmail_message_index
  for select to authenticated, anon
  using (true);

create policy if not exists gm_select_all
  on opsdashboard.gmail_messages
  for select to authenticated, anon
  using (true);

-- INSERT policies
create policy if not exists gmi_insert_all
  on opsdashboard.gmail_message_index
  for insert to authenticated, anon
  with check (true);

create policy if not exists gm_insert_all
  on opsdashboard.gmail_messages
  for insert to authenticated, anon
  with check (true);

-- UPDATE policies
create policy if not exists gmi_update_all
  on opsdashboard.gmail_message_index
  for update to authenticated, anon
  using (true) with check (true);

create policy if not exists gm_update_all
  on opsdashboard.gmail_messages
  for update to authenticated, anon
  using (true) with check (true);

-- (Tighten these later if you need per-user isolation; for now they’re open.)

-- ===============================
-- 4) KEEP updated_at FRESH ON UPDATE
-- ===============================
create or replace function opsdashboard.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists trg_gmail_messages_set_updated_at on opsdashboard.gmail_messages;
create trigger trg_gmail_messages_set_updated_at
before update on opsdashboard.gmail_messages
for each row execute function opsdashboard.set_updated_at();

-- ===============================
-- 5) PUBLIC VIEWS (UPDATABLE PASSTHROUGH)
-- Make simple 1:1 views so PostgREST tables live in `public`
-- ===============================
create or replace view public.gmail_message_index as
select id, thread_id, internal_ms, ymd, created_at
from opsdashboard.gmail_message_index;

create or replace view public.gmail_messages as
select id, thread_id, internal_ms, headers, snippet, body_full, raw_json, updated_at
from opsdashboard.gmail_messages;

-- IMPORTANT: run views as the caller so base-table RLS applies
alter view public.gmail_message_index set (security_invoker = true);
alter view public.gmail_messages     set (security_invoker = true);

-- Grants on the views themselves
grant select, insert, update on public.gmail_message_index to anon, authenticated;
grant select, insert, update on public.gmail_messages     to anon, authenticated;