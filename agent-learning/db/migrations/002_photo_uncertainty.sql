ALTER TABLE food_templates
    ADD COLUMN kcal_value INTEGER,
    ADD COLUMN uncertainty_pct NUMERIC(5,4);

UPDATE food_templates
SET kcal_value = ROUND((kcal_low + kcal_high) / 2.0),
    uncertainty_pct = CASE
        WHEN kcal_low + kcal_high = 0 THEN 0.10
        ELSE LEAST(0.60, GREATEST(0.05, (kcal_high - kcal_low)::NUMERIC / (kcal_low + kcal_high)))
    END;

ALTER TABLE food_templates
    ALTER COLUMN kcal_value SET NOT NULL,
    ALTER COLUMN uncertainty_pct SET NOT NULL,
    ADD CONSTRAINT food_templates_kcal_value_check CHECK (kcal_value >= 0),
    ADD CONSTRAINT food_templates_uncertainty_check CHECK (uncertainty_pct BETWEEN 0 AND 0.60);

ALTER TABLE meal_records
    ADD COLUMN estimate_confidence TEXT,
    ADD CONSTRAINT meal_records_estimate_confidence_check
        CHECK (estimate_confidence IS NULL OR estimate_confidence IN ('high', 'medium', 'low'));

ALTER TABLE meal_items
    ADD COLUMN estimate_confidence TEXT,
    ADD CONSTRAINT meal_items_estimate_confidence_check
        CHECK (estimate_confidence IS NULL OR estimate_confidence IN ('high', 'medium', 'low'));
