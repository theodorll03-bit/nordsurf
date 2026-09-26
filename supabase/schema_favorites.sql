-- Nordsurf: Supabase-skjema for Fase 3 (favoritter).
-- Kjøres i Supabase-dashbordet: SQL Editor -> New query -> lim inn -> Run.
-- Kjøres i tillegg til schema.sql (som må være kjørt fra før).
-- Inneholder ingen hemmeligheter, trygt å ha i repoet.

create table public.favorites (
  user_id uuid not null references auth.users(id) on delete cascade,
  spot_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, spot_id)
);

alter table public.favorites enable row level security;

-- Man kan bare se, legge til og fjerne sine egne favoritter.
create policy "Egne favoritter kan leses"
  on public.favorites for select
  using (auth.uid() = user_id);

create policy "Egne favoritter kan legges til"
  on public.favorites for insert
  with check (auth.uid() = user_id);

create policy "Egne favoritter kan fjernes"
  on public.favorites for delete
  using (auth.uid() = user_id);
