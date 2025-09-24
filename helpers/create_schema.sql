-- =========================================================
-- Schema
-- =========================================================
create schema if not exists opsdashboard;
create schema if not exists public;

-- =========================================================
-- Enum type for authorized_users.role
-- =========================================================
do $$
begin
  if not exists (
    select 1
    from pg_type t
    join pg_namespace n on n.oid = t.typnamespace
    where t.typname = 'roles' and n.nspname = 'public'
  ) then
    create type public.roles as enum ('guest');
  end if;
end$$;

-- =========================================================
-- authorized_users
-- =========================================================
create table if not exists opsdashboard.authorized_users (
  id           integer not null primary key,
  created_at   timestamptz default now(),
  email        text not null,
  role         public.roles default 'guest',
  updated_at   timestamptz default now()
);

create sequence if not exists opsdashboard.authorized_users_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.authorized_users_id_seq owned by opsdashboard.authorized_users.id;
alter table opsdashboard.authorized_users
  alter column id set default nextval('opsdashboard.authorized_users_id_seq');

-- =========================================================
-- brainstorms
-- =========================================================
create table if not exists opsdashboard.brainstorms (
  id           bigint not null primary key,
  created_at   timestamptz not null default now(),
  title        text,
  content      text,
  slide_json   jsonb
);

create sequence if not exists opsdashboard.brainstorms_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.brainstorms_id_seq owned by opsdashboard.brainstorms.id;
alter table opsdashboard.brainstorms
  alter column id set default nextval('opsdashboard.brainstorms_id_seq');

-- =========================================================
-- calendar_events
-- =========================================================
create table if not exists opsdashboard.calendar_events (
  event_id     integer not null primary key,
  summary      text not null,
  start_time   timestamptz default now(),
  end_time     timestamptz default now()
);

create sequence if not exists opsdashboard.calendar_events_event_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.calendar_events_event_id_seq owned by opsdashboard.calendar_events.event_id;
alter table opsdashboard.calendar_events
  alter column event_id set default nextval('opsdashboard.calendar_events_event_id_seq');

-- =========================================================
-- gm_tokens
-- =========================================================
create table if not exists opsdashboard.gm_tokens (
  id           bigint not null primary key,
  created_at   timestamptz not null default now(),
  token        jsonb,
  status       text not null default 'active',
  updated_at   timestamptz not null default now()
);

create sequence if not exists opsdashboard.gm_tokens_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.gm_tokens_id_seq owned by opsdashboard.gm_tokens.id;
alter table opsdashboard.gm_tokens
  alter column id set default nextval('opsdashboard.gm_tokens_id_seq');

-- =========================================================
-- research_program_students
-- (Converted PK to sequence-backed bigint)
-- =========================================================
create table if not exists opsdashboard.research_program_students (
  id                      bigint not null primary key,
  full_name               text not null,
  student_emails          json not null,
  parent_emails           json,
  primary_student_email   text,
  primary_parent_email    text,
  instructor_id           number default 10000,
  mentor_id               number default 10000
);

ALTER TABLE opsdashboard.research_program_students ADD COLUMN instuctor_name text;
ALTER TABLE opsdashboard.research_program_students ADD COLUMN mentor_name text;
ALTER TABLE opsdashboard.research_program_students ADD COLUMN ops_name text;

create sequence if not exists opsdashboard.research_program_students_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.research_program_students_id_seq owned by opsdashboard.research_program_students.id;
alter table opsdashboard.research_program_students
  alter column id set default nextval('opsdashboard.research_program_students_id_seq');

-- =========================================================
-- student_emails
-- =========================================================
create table if not exists opsdashboard.student_emails (
  id            bigint not null primary key,
  message_id    varchar not null,
  thread_id     varchar not null,
  internal_date timestamptz,
  snippet       varchar,
  payload       varchar,
  unique (message_id, thread_id)
);

create sequence if not exists opsdashboard.student_emails_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.student_emails_id_seq owned by opsdashboard.student_emails.id;
alter table opsdashboard.student_emails
  alter column id set default nextval('opsdashboard.student_emails_id_seq');

-- =========================================================
-- Instructors and mentors
-- =========================================================
create table if not exists opsdashboard.instructors (
  id            bigint not null primary key,
  name    varchar not null,
  email     varchar not null,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

create sequence if not exists opsdashboard.instructors_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.instructors_id_seq owned by opsdashboard.instructors.id;
alter table opsdashboard.instructors
  alter column id set default nextval('opsdashboard.instructors_id_seq');

-- =========================================================
-- waitlist
-- =========================================================
create table if not exists opsdashboard.waitlist (
  id           integer not null primary key,
  created_at   timestamptz default now(),
  email        text not null
);

create sequence if not exists opsdashboard.waitlist_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.waitlist_id_seq owned by opsdashboard.waitlist.id;
alter table opsdashboard.waitlist
  alter column id set default nextval('opsdashboard.waitlist_id_seq');

-- =========================================================
-- confluence_pages
-- (Converted PK to sequence-backed bigint)
-- =========================================================
create table if not exists opsdashboard.confluence_pages (
  id                      bigint not null primary key,
  full_name               text not null,
  title                   text,
  page_url                text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create sequence if not exists opsdashboard.confluence_pages_id_seq
  start with 10000 increment by 1;
alter sequence opsdashboard.confluence_pages_id_seq owned by opsdashboard.confluence_pages.id;
alter table opsdashboard.confluence_pages
  alter column id set default nextval('opsdashboard.confluence_pages_id_seq');

-- allow API roles to see the schema
grant usage on schema opsdashboard to anon, authenticated;

-- allow basic table privileges
grant select, insert, update, delete on opsdashboard.confluence_pages
  to anon, authenticated;

-- if you will insert (uses the sequence)
grant usage, select on sequence opsdashboard.confluence_pages_id_seq
  to anon, authenticated;

-- =========================================================
-- Public views + grants
-- =========================================================
create or replace view public.authorized_users as
  select * from opsdashboard.authorized_users;
grant select on public.authorized_users to anon, authenticated;

create or replace view public.brainstorms as
  select * from opsdashboard.brainstorms;
grant select on public.brainstorms to anon, authenticated;

create or replace view public.calendar_events as
  select * from opsdashboard.calendar_events;
grant select on public.calendar_events to anon, authenticated;

create or replace view public.gm_tokens as
  select * from opsdashboard.gm_tokens;
grant select on public.gm_tokens to anon, authenticated;

create or replace view public.research_program_students as
  select * from opsdashboard.research_program_students;
grant select,update on public.research_program_students to anon, authenticated;

grant usage, select on sequence opsdashboard.research_program_students_id_seq to authenticated, anon;

create or replace view public.student_emails as
  select * from opsdashboard.student_emails;
grant select on public.student_emails to anon, authenticated;

create or replace view public.waitlist as
  select * from opsdashboard.waitlist;
grant select on public.waitlist to anon, authenticated;

create or replace view public.instructors as
  select * from opsdashboard.instructors;
grant select on public.instructors to anon, authenticated;

-- 1. Create a simple pass-through view
create or replace view public.confluence_pages as
  select * from opsdashboard.confluence_pages;

-- 2. Ensure it runs with caller’s rights
alter view public.confluence_pages set (security_invoker = true);

-- 3. Grant privileges on both the view and underlying schema/table
grant usage on schema opsdashboard to anon, authenticated;
grant select, update on opsdashboard.confluence_pages to anon, authenticated;
grant select, update on public.confluence_pages to anon, authenticated;

-- 4. Enable and add RLS policies on the base table
alter table opsdashboard.confluence_pages enable row level security;

create policy allow_select
on opsdashboard.confluence_pages
for select to authenticated
using (true);

create policy allow_update
on opsdashboard.confluence_pages
for update to authenticated
using (true)
with check (true);

-- allow API roles to use the schema
grant usage on schema opsdashboard to anon, authenticated, service_role;

-- allow API roles to read/write all existing tables in the schema
grant all on all tables in schema opsdashboard to anon, authenticated, service_role;

-- allow API roles to use all sequences in the schema (needed for nextval)
grant all on all sequences in schema opsdashboard to anon, authenticated, service_role;

-- make sure future tables/sequences inherit these privileges
alter default privileges for role postgres in schema opsdashboard
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema opsdashboard
  grant all on sequences to anon, authenticated, service_role;

-- Function calls to avoid access issues
create or replace function public.update_contact_by_full_name(
  p_full_name text,
  p_instructor text,
  p_mentor text,
  p_ops text
)
returns setof opsdashboard.research_program_students
language sql
security definer
as $$
  update opsdashboard.research_program_students
     set instuctor_name  = p_instructor,
         mentor_name  = p_mentor,
         ops_name = p_ops
   where full_name = p_full_name
   returning *;
$$;

-- add a policy that allows calling this function if needed
grant execute on function public.update_contact_by_full_name(text, text, text, text)
  to authenticated;