-- Run in the Supabase SQL editor after Flask migrations.
do $$ begin
  create type public.app_role as enum ('super_admin', 'admin', 'counsellor', 'student');
exception when duplicate_object then null;
end $$;

create table if not exists public.profiles (
  id uuid primary key,
  email text not null unique,
  full_name text not null,
  avatar_url text,
  role text not null default 'student' check (role in ('super_admin','admin','counsellor','student')),
  email_verified boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login_at timestamptz
);

alter table public.profiles add column if not exists avatar_url text;

do $$ begin
  alter table public.profiles
    add constraint profiles_auth_user_fk foreign key (id) references auth.users(id) on delete cascade not valid;
exception when duplicate_object then null;
end $$;

create index if not exists ix_profiles_role on public.profiles(role);
create index if not exists ix_profiles_is_active on public.profiles(is_active);
create index if not exists ix_profiles_created_at on public.profiles(created_at);

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, full_name, role, email_verified)
  values (
    new.id,
    lower(coalesce(new.email, '')),
    left(coalesce(new.raw_user_meta_data ->> 'full_name', split_part(coalesce(new.email, ''), '@', 1), 'User'), 120),
    'student',
    new.email_confirmed_at is not null
  )
  on conflict (id) do nothing;
  return new;
exception when others then
  raise warning 'Profile creation failed for auth user %', new.id;
  return new;
end;
$$;

revoke all on function public.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own on public.profiles for select to authenticated using (id = auth.uid());
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- RLS limits rows, not columns. Keep authorization fields server-controlled.
revoke all on public.profiles from anon;
revoke all on public.profiles from authenticated;
grant select on public.profiles to authenticated;
grant update (full_name, avatar_url) on public.profiles to authenticated;
grant all on public.profiles to service_role;

do $$
declare
  table_name text;
  owned_tables text[] := array[
    'career_assessments','resume_scans','learning_progress','career_profiles',
    'career_roadmaps','user_learning_resources','resume_documents',
    'interview_sessions','chat_conversations'
  ];
begin
  foreach table_name in array owned_tables loop
    if to_regclass('public.' || table_name) is not null then
      execute format('alter table public.%I enable row level security', table_name);
      execute format('drop policy if exists %I on public.%I', table_name || '_select_own', table_name);
      execute format('create policy %I on public.%I for select to authenticated using (user_id = auth.uid())', table_name || '_select_own', table_name);
      execute format('drop policy if exists %I on public.%I', table_name || '_insert_own', table_name);
      execute format('create policy %I on public.%I for insert to authenticated with check (user_id = auth.uid())', table_name || '_insert_own', table_name);
      execute format('drop policy if exists %I on public.%I', table_name || '_update_own', table_name);
      execute format('create policy %I on public.%I for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid())', table_name || '_update_own', table_name);
      execute format('drop policy if exists %I on public.%I', table_name || '_delete_own', table_name);
      execute format('create policy %I on public.%I for delete to authenticated using (user_id = auth.uid())', table_name || '_delete_own', table_name);
    end if;
  end loop;
end $$;

insert into storage.buckets (id, name, public)
values ('career-documents', 'career-documents', false)
on conflict (id) do update set public = false;

drop policy if exists career_documents_select_own on storage.objects;
create policy career_documents_select_own on storage.objects for select to authenticated
using (bucket_id = 'career-documents' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists career_documents_insert_own on storage.objects;
create policy career_documents_insert_own on storage.objects for insert to authenticated
with check (bucket_id = 'career-documents' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists career_documents_delete_own on storage.objects;
create policy career_documents_delete_own on storage.objects for delete to authenticated
using (bucket_id = 'career-documents' and (storage.foldername(name))[1] = auth.uid()::text);
