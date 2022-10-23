-- Fix order by on v_budgets
DROP VIEW comptasso.v_budgets;

CREATE OR REPLACE VIEW comptasso.v_budgets
AS SELECT b.id_budget,
    b.name,
    b.reference,
    f.id_funder,
    f.name AS funder,
    bt.label AS type_budget,
    COALESCE(b.date_max_expenditure::text, '-'::text) AS date_max_expenditure,
    COALESCE(b.date_return::text, '-'::text) AS date_return,
    COALESCE(b.budget_amount, 0::numeric)::numeric(8,2) AS budget_amount,
    COALESCE(b.payroll_limit, 0::numeric)::numeric(8,2) AS payroll_limit,
    COALESCE(b.indirect_charges, 0::numeric)::numeric(8,2) AS indirect_charges,
    COALESCE(b.indirect_charges / 100::numeric * b.payroll_limit, 0::numeric)::numeric(8,2) AS indirect_charges_amount,
    b.comment,
    b.active,
    comptasso.get_sum_movement(b.id_budget, 'Recette'::text) AS received_amount,
    (comptasso.get_sum_movement(b.id_budget, 'Recette'::text) / b.budget_amount * 100::numeric)::numeric(8,2) AS percent_received,
    comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) AS spent_amount,
    (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) / b.budget_amount * 100::numeric)::numeric(8,2) AS percent_spent,
    comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) AS committed_amount,
    (comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) / b.budget_amount * 100::numeric)::numeric(8,2) AS percent_committed,
    b.budget_amount - (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) + comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)) AS available_amount,
    COALESCE(max(op.effective_date)::text, '-'::text) AS last_operation,
    COALESCE(max(cab.date_action)::text, '-'::text) AS last_action_date
   FROM comptasso.t_budgets b
     LEFT JOIN comptasso.dict_budget_types bt ON b.id_type_budget = bt.id_type_budget
     LEFT JOIN comptasso.t_funders f ON f.id_funder = b.id_funder
     LEFT JOIN comptasso.t_operations op ON op.id_budget = b.id_budget
     LEFT JOIN comptasso.cor_action_budget cab ON cab.id_budget = b.id_budget
  GROUP BY b.id_budget, b.name, b.reference, f.id_funder, f.name, bt.label, b.date_max_expenditure, b.date_return, b.budget_amount, b.payroll_limit, b.indirect_charges, b.comment, b.active, (comptasso.get_sum_movement(b.id_budget, 'Recette'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Recette'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (b.budget_amount - (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) + comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)))
  ORDER BY b.active DESC, b.name ASC;

-- Done on server
INSERT INTO comptasso.dict_categories (cd_category, "label", detail, "level", cd_broader, id_type_operation, seizable)
VALUES (65, 'Autres charges de gestion courante (redevances, cotisations...)', 'Autres charges liées aux activités et à la gestion courante de l''association : redevances, cotisations, subventions versées ...',1,65,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE "label"='Dépense'),true ),
(67, 'Charges exceptionnelles (amendes, créances, pénalités...)', 'Charges exceptionnelles : créances, amendes, pénalités, rappels d''imposition...',1,65,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE "label"='Dépense'),true );

INSERT INTO comptasso.dict_categories (cd_category, label, detail, level, cd_broader, id_type_operation, seizable)
VALUES
('648','Autres charges de personnels (gratifications, indemnités de stage...)','Gratifications et indemnités de stages, services civiques etc',2,64,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),

UPDATE comptasso.dict_categories
SET seizable=true,
label = 'Charges de personnel (salaires, primes, prélèvements urssaf...)'
WHERE cd_category=64;

UPDATE comptasso.dict_categories
SET seizable=false
WHERE cd_category IN (641,645);