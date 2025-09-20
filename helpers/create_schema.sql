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
  token        jsonb
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
  primary_parent_email    text
);

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
grant select on public.research_program_students to anon, authenticated;

grant usage, select on sequence opsdashboard.research_program_students_id_seq to authenticated, anon;

create or replace view public.student_emails as
  select * from opsdashboard.student_emails;
grant select on public.student_emails to anon, authenticated;

create or replace view public.waitlist as
  select * from opsdashboard.waitlist;
grant select on public.waitlist to anon, authenticated;

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