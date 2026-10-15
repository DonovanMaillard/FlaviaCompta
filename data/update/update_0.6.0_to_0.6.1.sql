-- Fix synthese by activity
DROP VIEW comptasso.v_synthese_activities;

CREATE OR REPLACE VIEW comptasso.v_synthese_activities AS
WITH r AS (SELECT 
    id_budget,
    sum(amount) AS received
    FROM comptasso.t_operations op 
    JOIN comptasso.dict_operation_types dot ON op.id_type_operation = dot.id_type_operation 
    WHERE dot."label" ='Recette'
    GROUP BY id_budget
    )
SELECT 
a.id_activity, 
a."label",
a.description,
a.active,
sum(b.budget_amount) - sum(r.received) AS to_receive,
sum(b.budget_amount) AS global_amount,
COUNT(b.id_budget) FILTER (WHERE b.date_closing IS NULL) AS active_budgets
FROM comptasso.t_activities a 
LEFT JOIN comptasso.t_budgets b ON b.id_activity = a.id_activity 
LEFT JOIN r ON r.id_budget = b.id_budget
WHERE b.date_closing IS NULL
GROUP BY 1,2
;