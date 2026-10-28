-- ==============================================================================
-- RADIX Platform — Unified Supabase Database Schema
-- Run this in your Supabase SQL Editor (https://supabase.com/dashboard/project/_/sql)
-- ==============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Candidate Profiles Table (Role 3 & Frontend)
CREATE TABLE IF NOT EXISTS public.profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    email TEXT,
    headline TEXT,
    location TEXT,
    profile_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON public.profiles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_gin_data ON public.profiles USING gin (profile_data);

-- 3. Profile Skills Table (Role 3, 4, 5)
CREATE TABLE IF NOT EXISTS public.profile_skills (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES public.profiles(profile_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    category_code TEXT NOT NULL CHECK (
        category_code IN ('COD', 'DSA', 'OOD', 'APTI', 'COMM', 'AI', 'CLOUD', 'SQL', 'SWE', 'SYSD', 'NETW', 'OS', 'OTHER')
    ),
    evidence TEXT DEFAULT '',
    confidence TEXT DEFAULT 'medium',
    source TEXT NOT NULL DEFAULT 'extracted',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_profile_skills_profile_id ON public.profile_skills(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_skills_category_code ON public.profile_skills(category_code);
CREATE INDEX IF NOT EXISTS idx_profile_skills_skill_name ON public.profile_skills(skill_name);

-- 4. Job Descriptions Table (Role 1)
CREATE TABLE IF NOT EXISTS public.job_descriptions (
    jd_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file TEXT NOT NULL,
    company TEXT,
    role TEXT,
    raw_text TEXT,
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_jds_created_at ON public.job_descriptions(created_at DESC);

-- 5. Assessments Table (Role 5 & Frontend)
CREATE TABLE IF NOT EXISTS public.assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(profile_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    company TEXT NOT NULL,
    jd_file TEXT,
    match_score NUMERIC NOT NULL,
    matched_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    partial_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    improvement_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    talent_check JSONB,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_assessments_profile_id ON public.assessments(profile_id);
CREATE INDEX IF NOT EXISTS idx_assessments_created_at ON public.assessments(created_at DESC);

-- 6. Row Level Security (RLS) - Permissive policies for hackathon / development
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profile_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public full access on profiles') THEN
        CREATE POLICY "Allow public full access on profiles" ON public.profiles FOR ALL USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public full access on profile_skills') THEN
        CREATE POLICY "Allow public full access on profile_skills" ON public.profile_skills FOR ALL USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public full access on job_descriptions') THEN
        CREATE POLICY "Allow public full access on job_descriptions" ON public.job_descriptions FOR ALL USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public full access on assessments') THEN
        CREATE POLICY "Allow public full access on assessments" ON public.assessments FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;
