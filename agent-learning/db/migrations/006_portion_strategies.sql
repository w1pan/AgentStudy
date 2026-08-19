ALTER TABLE meal_items
    ADD COLUMN portion_basis TEXT,
    ADD COLUMN portion_detail TEXT,
    ADD COLUMN portion_confidence TEXT,
    ADD COLUMN density_confidence TEXT,
    ADD CONSTRAINT meal_items_portion_basis_check
        CHECK (
            portion_basis IS NULL
            OR portion_basis IN ('count', 'container', 'package', 'geometry', 'mixed', 'visual')
        ),
    ADD CONSTRAINT meal_items_portion_confidence_check
        CHECK (
            portion_confidence IS NULL
            OR portion_confidence IN ('high', 'medium', 'low')
        ),
    ADD CONSTRAINT meal_items_density_confidence_check
        CHECK (
            density_confidence IS NULL
            OR density_confidence IN ('high', 'medium', 'low')
        );
