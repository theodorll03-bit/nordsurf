-- Nordsurf: Supabase-skjema for Fase 4 (rapporter/kommentarer).
-- Kjøres i Supabase-dashbordet: SQL Editor -> New query -> lim inn -> Run.
-- Krever at pg_cron-extensionen er skrudd på FØRST (Database -> Extensions
-- -> søk "pg_cron" -> Enable), ellers feiler cron.schedule() nederst.
-- Kjøres i tillegg til schema.sql og schema_favorites.sql (må kjøres fra før).
-- Inneholder ingen hemmeligheter, trygt å ha i repoet.

-- user_id peker på profiles (ikke auth.users direkte), slik at PostgREST kan
-- hente visningsnavnet sammen med rapporten, og slik at man må ha satt et
-- visningsnavn før man kan skrive en rapport.
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  spot_id text not null,
  user_id uuid not null references public.profiles(id) on delete cascade,
  text text not null check (char_length(text) between 1 and 500),
  wave_height_m numeric,
  wind_impression text check (wind_impression in ('offshore','onshore','side','stille')),
  created_at timestamptz not null default now()
);

alter table public.reports enable row level security;

create policy "Innloggede kan lese rapporter"
  on public.reports for select
  using (auth.uid() is not null);

create policy "Innloggede kan skrive egne rapporter"
  on public.reports for insert
  with check (
    auth.uid() = user_id
    and not exists (select 1 from public.profiles p where p.id = auth.uid() and p.banned)
  );

create policy "Egne rapporter kan slettes"
  on public.reports for delete
  using (auth.uid() = user_id);

-- Anonymisert arkiv: ingen user_id, bare innhold og tidspunkt.
create table public.reports_archive (
  id uuid primary key default gen_random_uuid(),
  spot_id text not null,
  text text not null,
  wave_height_m numeric,
  wind_impression text,
  created_at timestamptz not null,
  archived_at timestamptz not null default now()
);

alter table public.reports_archive enable row level security;

create policy "Innloggede kan lese arkiverte rapporter"
  on public.reports_archive for select
  using (auth.uid() is not null);

-- Flytter rapporter eldre enn 7 dager til arkivet (anonymisert), og sletter
-- arkiverte rader eldre enn 2 år. security definer -> kjører som eieren
-- (postgres), som eier tabellene og derfor ikke er bundet av RLS-policyene
-- over (de gjelder bare vanlige innloggede brukere via PostgREST).
create or replace function public.archive_and_purge_reports()
returns void as $$
begin
  insert into public.reports_archive (spot_id, text, wave_height_m, wind_impression, created_at)
  select spot_id, text, wave_height_m, wind_impression, created_at
  from public.reports
  where created_at < now() - interval '7 days';

  delete from public.reports
  where created_at < now() - interval '7 days';

  delete from public.reports_archive
  where archived_at < now() - interval '2 years';
end;
$$ language plpgsql security definer set search_path = public;

select cron.schedule(
  'archive-and-purge-reports',
  '0 3 * * *',
  $$select public.archive_and_purge_reports()$$
);
