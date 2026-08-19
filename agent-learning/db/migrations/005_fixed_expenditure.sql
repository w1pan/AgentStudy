UPDATE daily_summaries
SET
    baseline_low = ROUND(rmr_kcal * 1.2),
    baseline_high = ROUND(rmr_kcal * 1.2),
    expenditure_low = ROUND(rmr_kcal * 1.2) + ROUND((exercise_low + exercise_high) / 2.0),
    expenditure_high = ROUND(rmr_kcal * 1.2) + ROUND((exercise_low + exercise_high) / 2.0),
    deficit_low = ROUND(rmr_kcal * 1.2) + ROUND((exercise_low + exercise_high) / 2.0) - intake_high,
    deficit_high = ROUND(rmr_kcal * 1.2) + ROUND((exercise_low + exercise_high) / 2.0) - intake_low,
    risk_flags = array_remove(risk_flags, 'target_below_rmr') ||
        CASE
            WHEN ROUND(rmr_kcal * 1.2) - target_high < rmr_kcal
                THEN ARRAY['target_below_rmr']::TEXT[]
            ELSE ARRAY[]::TEXT[]
        END,
    data_version = data_version + 1,
    updated_at = NOW()
WHERE record_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Shanghai')::DATE;
