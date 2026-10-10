-- Canonical KPI queries. kpi.py splits on '-- name: ' markers (single source).
-- name: deduped
SELECT * FROM deals WHERE id IN (SELECT MIN(id) FROM deals GROUP BY ext_id);
-- name: win_rate
SELECT SUM(CASE WHEN stage='won' THEN 1 ELSE 0 END) AS won,
       SUM(CASE WHEN stage='lost' THEN 1 ELSE 0 END) AS lost
FROM deals WHERE id IN (SELECT MIN(id) FROM deals GROUP BY ext_id);
-- name: won_amounts
SELECT amount_eur FROM deals
WHERE id IN (SELECT MIN(id) FROM deals GROUP BY ext_id)
  AND stage='won' AND amount_eur IS NOT NULL ORDER BY amount_eur;
-- name: duplicates
SELECT COUNT(*) FROM (SELECT ext_id FROM deals GROUP BY ext_id HAVING COUNT(*) > 1) d;
-- name: missing_amount
SELECT COUNT(*) FROM deals
WHERE id IN (SELECT MIN(id) FROM deals GROUP BY ext_id) AND amount_eur IS NULL;
-- name: unknown_stage
SELECT ext_id FROM deals
WHERE id IN (SELECT MIN(id) FROM deals GROUP BY ext_id) AND stage IS NULL;
-- name: enablement
SELECT SUM(CASE WHEN done THEN 1 ELSE 0 END) AS done, COUNT(*) AS total FROM enablement;
