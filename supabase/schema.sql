-- Nordsurf: Supabase-skjema for Fase 2 (innlogging og visningsnavn).
-- Kjøres i Supabase-dashbordet: SQL Editor -> New query -> lim inn -> Run.
-- Inneholder ingen hemmeligheter, trygt å ha i repoet.

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  is_admin boolean not null default false,
  banned boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Alle innloggede kan se visningsnavn (trengs for kommentarer i fase 4).
create policy "Alle kan lese profiler"
  on public.profiles for select
  using (true);

-- Man kan bare opprette sin egen profil.
create policy "Egen profil kan opprettes"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Man kan bare endre sin egen profil (is_admin/banned låses av trigger under).
create policy "Egen profil kan endres"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Man kan bare slette sin egen profil.
create policy "Egen profil kan slettes"
  on public.profiles for delete
  using (auth.uid() = id);

-- Sikrer at is_admin/banned ikke kan endres via vanlig klient-oppdatering,
-- selv om noen skulle klare å sende de feltene med. Kjører ikke når en
-- admin endrer via SQL Editor (der er auth.uid() null).
create or replace function public.protect_profile_admin_fields()
returns trigger as $$
begin
  if auth.uid() is not null then
    new.is_admin := old.is_admin;
    new.banned := old.banned;
  end if;
  return new;
end;
$$ language plpgsql security definer;

create trigger protect_profile_admin_fields
  before update on public.profiles
  for each row execute function public.protect_profile_admin_fields();
