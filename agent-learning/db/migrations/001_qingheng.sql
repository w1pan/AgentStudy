CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    age SMALLINT NOT NULL CHECK (age BETWEEN 18 AND 64),
    biological_sex TEXT NOT NULL CHECK (biological_sex IN ('male', 'female')),
    height_cm NUMERIC(5,2) NOT NULL CHECK (height_cm BETWEEN 120 AND 230),
    current_weight_kg NUMERIC(6,2) NOT NULL CHECK (current_weight_kg BETWEEN 30 AND 300),
    deficit_preset TEXT NOT NULL CHECK (deficit_preset IN ('gentle', 'standard')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS weight_records (
    user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    weight_kg NUMERIC(6,2) NOT NULL CHECK (weight_kg BETWEEN 30 AND 300),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, record_date)
);

CREATE TABLE IF NOT EXISTS food_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    category TEXT NOT NULL,
    kcal_low INTEGER NOT NULL CHECK (kcal_low >= 0),
    kcal_high INTEGER NOT NULL CHECK (kcal_high >= kcal_low),
    units JSONB NOT NULL,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    source_url TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS food_templates_name_idx ON food_templates (name);

CREATE TABLE IF NOT EXISTS met_activities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    met_low NUMERIC(4,1) NOT NULL,
    met_medium NUMERIC(4,1) NOT NULL,
    met_high NUMERIC(4,1) NOT NULL,
    source_version TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS meal_records (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    recorded_time TIME NOT NULL,
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'custom')),
    custom_meal_name TEXT,
    entry_method TEXT NOT NULL CHECK (entry_method IN ('manual', 'photo')),
    kcal_low INTEGER NOT NULL CHECK (kcal_low >= 0),
    kcal_high INTEGER NOT NULL CHECK (kcal_high >= kcal_low),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((meal_type = 'custom' AND custom_meal_name IS NOT NULL) OR (meal_type <> 'custom' AND custom_meal_name IS NULL))
);

CREATE INDEX IF NOT EXISTS meal_records_user_date_idx ON meal_records (user_id, record_date, recorded_time);

CREATE TABLE IF NOT EXISTS meal_items (
    id UUID PRIMARY KEY,
    meal_id UUID NOT NULL REFERENCES meal_records(id) ON DELETE CASCADE,
    template_id TEXT REFERENCES food_templates(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    unit TEXT NOT NULL,
    grams_low INTEGER,
    grams_high INTEGER,
    kcal_low INTEGER NOT NULL CHECK (kcal_low >= 0),
    kcal_high INTEGER NOT NULL CHECK (kcal_high >= kcal_low),
    estimate_source TEXT NOT NULL CHECK (estimate_source IN ('template', 'user', 'ai')),
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exercise_records (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    activity_id TEXT NOT NULL REFERENCES met_activities(id),
    activity_name TEXT NOT NULL,
    intensity TEXT NOT NULL CHECK (intensity IN ('low', 'medium', 'high')),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes BETWEEN 1 AND 600),
    record_date DATE NOT NULL,
    recorded_time TIME NOT NULL,
    kcal_low INTEGER NOT NULL CHECK (kcal_low >= 0),
    kcal_high INTEGER NOT NULL CHECK (kcal_high >= kcal_low),
    estimate_source TEXT NOT NULL CHECK (estimate_source IN ('met', 'manual_adjusted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS exercise_records_user_date_idx ON exercise_records (user_id, record_date, recorded_time);

CREATE TABLE IF NOT EXISTS daily_summaries (
    user_id TEXT NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    data_version INTEGER NOT NULL DEFAULT 1 CHECK (data_version >= 1),
    rmr_kcal INTEGER NOT NULL,
    weight_kg NUMERIC(6,2) NOT NULL,
    profile_snapshot JSONB NOT NULL,
    intake_low INTEGER NOT NULL,
    intake_high INTEGER NOT NULL,
    baseline_low INTEGER NOT NULL,
    baseline_high INTEGER NOT NULL,
    exercise_low INTEGER NOT NULL,
    exercise_high INTEGER NOT NULL,
    expenditure_low INTEGER NOT NULL,
    expenditure_high INTEGER NOT NULL,
    deficit_low INTEGER NOT NULL,
    deficit_high INTEGER NOT NULL,
    target_low INTEGER NOT NULL,
    target_high INTEGER NOT NULL,
    risk_flags TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, record_date)
);
