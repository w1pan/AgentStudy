UPDATE daily_summaries
SET
    baseline_low = ROUND(rmr_kcal * 1.2 * 0.97),
    baseline_high = ROUND(rmr_kcal * 1.2 * 1.03),
    expenditure_low = ROUND(rmr_kcal * 1.2 * 0.97) + exercise_low,
    expenditure_high = ROUND(rmr_kcal * 1.2 * 1.03) + exercise_high,
    deficit_low = ROUND(rmr_kcal * 1.2 * 0.97) + exercise_low - intake_high,
    deficit_high = ROUND(rmr_kcal * 1.2 * 1.03) + exercise_high - intake_low,
    risk_flags = array_remove(risk_flags, 'target_below_rmr') ||
        CASE
            WHEN ROUND(rmr_kcal * 1.2 * 0.97) - target_high < rmr_kcal
                THEN ARRAY['target_below_rmr']::TEXT[]
            ELSE ARRAY[]::TEXT[]
        END,
    data_version = data_version + 1,
    updated_at = NOW()
WHERE record_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Shanghai')::DATE;
