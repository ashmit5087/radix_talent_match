-- Role 1 (JD Analytics) tables. Run once in the Supabase SQL Editor (or `supabase db push`).

create table if not exists public.jd_analyses (
    id              uuid primary key default gen_random_uuid(),
    source_file     text not null,
    company         text,
    role            text,
    indexing_status text not null check (indexing_status in ('indexed', 'failed')),
    chunk_count     integer not null default 0,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create table if not exists public.jd_skills (
    id            uuid primary key default gen_random_uuid(),
    jd_id         uuid not null references public.jd_analyses(id) on delete cascade,
    skill_name    text not null,
    category_code text not null check (category_code in
        ('COD','DSA','OOD','APTI','COMM','AI','CLOUD','SQL','SWE','SYSD','NETW','OS','OTHER')),
    evidence      text not null,
    confidence    text not null check (confidence in ('high','medium','low')),
    position      integer not null default 0          -- keeps the order the skills were returned in
);
create unique index if not exists jd_skills_unique_name on public.jd_skills (jd_id, lower(skill_name));
create index if not exists jd_skills_jd_id_idx on public.jd_skills (jd_id);

-- Only the backend (service-role key) may touch these tables. RLS on + no policies = anon/public blocked.
alter table public.jd_analyses enable row level security;
alter table public.jd_skills   enable row level security;

-- Atomic save: analysis row + all its skills in ONE transaction.
create or replace function public.save_jd_analysis(
    p_id uuid, p_source_file text, p_company text, p_role text,
    p_status text, p_chunks integer, p_skills jsonb
) returns void language plpgsql as $$
begin
    insert into public.jd_analyses (id, source_file, company, role, indexing_status, chunk_count)
    values (p_id, p_source_file, p_company, p_role, p_status, p_chunks);

    insert into public.jd_skills (jd_id, skill_name, category_code, evidence, confidence, position)
    select p_id, s->>'skill_name', s->>'category_code', s->>'evidence', s->>'confidence', (ord - 1)::int
    from jsonb_array_elements(p_skills) with ordinality as t(s, ord);
end $$;

-- Atomic replace of a JD's skills (used by PATCH). Returns false if the jd_id does not exist.
create or replace function public.replace_jd_skills(p_jd_id uuid, p_skills jsonb)
returns boolean language plpgsql as $$
begin
    update public.jd_analyses set updated_at = now() where id = p_jd_id;
    if not found then
        return false;
    end if;
    delete from public.jd_skills where jd_id = p_jd_id;
    insert into public.jd_skills (jd_id, skill_name, category_code, evidence, confidence, position)
    select p_jd_id, s->>'skill_name', s->>'category_code', s->>'evidence', s->>'confidence', (ord - 1)::int
    from jsonb_array_elements(p_skills) with ordinality as t(s, ord);
    return true;
end $$;

-- Functions are callable only with the service-role key.
revoke execute on function public.save_jd_analysis(uuid, text, text, text, text, integer, jsonb) from public, anon, authenticated;
revoke execute on function public.replace_jd_skills(uuid, jsonb) from public, anon, authenticated;
