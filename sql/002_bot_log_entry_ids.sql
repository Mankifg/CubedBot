-- Make database-log batch retries idempotent on existing installations.
-- Safe to run while the previous bot version is still active.

begin;

set local lock_timeout = '5s';
set local statement_timeout = '30s';

alter table public.bot_logs
    add column if not exists entry_id uuid default gen_random_uuid();

update public.bot_logs
set entry_id = gen_random_uuid()
where entry_id is null;

alter table public.bot_logs
    alter column entry_id set default gen_random_uuid(),
    alter column entry_id set not null;

create unique index if not exists bot_logs_entry_id_idx
    on public.bot_logs (entry_id);

commit;
