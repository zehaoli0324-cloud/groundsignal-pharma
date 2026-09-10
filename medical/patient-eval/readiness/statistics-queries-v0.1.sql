-- Q1 病例完成情况。病例是独立场景；会话包含流程分支和重复运行。
WITH base_units AS (
  SELECT case_id, COUNT(*) AS units
  FROM (SELECT DISTINCT case_id, platform, arm FROM sessions)
  GROUP BY case_id
)
SELECT c.case_id, c.family_id, COUNT(s.session_id) AS sessions,
       COUNT(s.session_id) - COALESCE(b.units, 0) AS repeat_sessions,
       COALESCE(SUM(s.status = 'completed'), 0) AS completed_sessions,
       COALESCE(SUM(s.status = 'target_error'), 0) AS target_error_sessions,
       COALESCE(SUM(s.status = 'measurement_invalid'), 0) AS measurement_invalid_sessions,
       COALESCE(SUM(s.status IN ('completed', 'target_error')), 0) AS target_metric_sessions
FROM cases c LEFT JOIN sessions s ON s.case_id = c.case_id
LEFT JOIN base_units b ON b.case_id = c.case_id
GROUP BY c.case_id, c.family_id, b.units ORDER BY c.case_id;

-- Q2 错误类别分布。目标服务失败与测量无效分开，不展示成功会话。
SELECT status AS session_status,
       CASE WHEN status = 'measurement_invalid' THEN invalid_component
            ELSE termination_reason END AS error_class,
       COUNT(*) AS sessions
FROM sessions WHERE status != 'completed'
GROUP BY session_status, error_class ORDER BY session_status, error_class;

-- Q3 两名指定评审者都实际完成质量评分的条目。
SELECT o.item_id, s.case_id, o.session_id, o.criterion_id,
       MAX(CASE WHEN r.reviewer_id = :reviewer_a THEN r.rating END) AS reviewer_a_rating,
       MAX(CASE WHEN r.reviewer_id = :reviewer_b THEN r.rating END) AS reviewer_b_rating
FROM opportunities o JOIN sessions s ON s.session_id = o.session_id
LEFT JOIN ratings r ON r.item_id = o.item_id
GROUP BY o.item_id, s.case_id, o.session_id, o.criterion_id
HAVING SUM(r.reviewer_id = :reviewer_a AND r.quality_status = 'assessed' AND r.rating IS NOT NULL) > 0
   AND SUM(r.reviewer_id = :reviewer_b AND r.quality_status = 'assessed' AND r.rating IS NOT NULL) > 0
ORDER BY o.item_id;
