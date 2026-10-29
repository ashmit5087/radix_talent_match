-- ==============================================================================
-- Migration: 001_create_profiles.sql
-- Module: RADIX Talent Match - Role 3 (Profile Builder)
-- Target Database: Supabase PostgreSQL
-- ==============================================================================

-- Enable UUID extension if not already present
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. Table: profiles
-- Stores master candidate profile records. profile_data contains the full canonical
-- profile document (personal_info, education, projects, certifications, etc.)
-- for high-performance sub-millisecond retrieval without multiple relational joins.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    profile_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for profiles
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles (email);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON public.profiles (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_gin_data ON public.profiles USING gin (profile_data);

-- ------------------------------------------------------------------------------
-- 2. Table: profile_skills
-- Stores normalized skills for each candidate profile.
-- Consumed directly by Role 4 (Talent Check) and Role 5 (Skill Matching).
-- Category codes strictly adhere to: COD, DSA, OOD, APTI, COMM, AI, CLOUD, SQL,
-- SWE, SYSD, NETW, OS, OTHER.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profile_skills (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES public.profiles(profile_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    category_code TEXT NOT NULL CHECK (
        category_code IN ('COD', 'DSA', 'OOD', 'APTI', 'COMM', 'AI', 'CLOUD', 'SQL', 'SWE', 'SYSD', 'NETW', 'OS', 'OTHER')
    ),
    evidence TEXT NOT NULL,
    confidence TEXT NOT NULL, -- Certainty score or level ('high', '0.9', etc.), NOT proficiency
    source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'extracted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Indexes for profile_skills
CREATE INDEX IF NOT EXISTS idx_profile_skills_profile_id ON public.profile_skills (profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_skills_category_code ON public.profile_skills (category_code);
CREATE INDEX IF NOT EXISTS idx_profile_skills_skill_name ON public.profile_skills (skill_name);

-- ------------------------------------------------------------------------------
-- 3. Row Level Security (RLS)
-- Grants read/write access to public anon/service roles for hackathon evaluation.
-- ------------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profile_skills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access on profiles"
    ON public.profiles FOR SELECT
    USING (true);

CREATE POLICY "Allow public insert/update on profiles"
    ON public.profiles FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow public read access on profile_skills"
    ON public.profile_skills FOR SELECT
    USING (true);

CREATE POLICY "Allow public insert/update on profile_skills"
    ON public.profile_skills FOR ALL
    USING (true)
    WITH CHECK (true);

-- ------------------------------------------------------------------------------
-- 4. Automatic updated_at Trigger
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_profile_timestamp ON public.profiles;

CREATE TRIGGER trigger_update_profile_timestamp
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_profile_updated_at();

COMMENT ON TABLE public.profiles IS 'RADIX Talent Match - Candidate Profiles (Role 3)';
COMMENT ON TABLE public.profile_skills IS 'Candidate Skills schema queried by Role 4 (Talent Check) & Role 5 (Skill Matching)';
