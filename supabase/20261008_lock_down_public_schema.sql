-- Run in the Foodbridge Supabase SQL Editor after reviewing the inventory output.
-- This script intentionally does not create client-access policies: this Django
-- application uses server-side sessions and should be its own data-access layer.

begin;

-- Remove direct REST API access from Supabase browser roles.
revoke all privileges on all tables in schema public from anon, authenticated;
revoke all privileges on all sequences in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;

-- Turn on RLS for every ordinary or partitioned table in public.
do $$
declare
  target record;
begin
  for target in
    select n.nspname as schema_name, c.relname as table_name
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relkind in ('r', 'p')
      and not c.relrowsecurity
  loop
    execute format('alter table %I.%I enable row level security', target.schema_name, target.table_name);
  end loop;
end
$$;

commit;

-- Verification: this must return no rows for application tables.
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
order by table_name, grantee, privilege_type;
