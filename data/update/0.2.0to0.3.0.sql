-- Add projet
CREATE TABLE comptasso.t_activities (
	id_activity serial primary key,
	label varchar(255) NOT NULL,
	description text,
	active boolean
);

-- A ajuster au contexte
INSERT INTO comptasso.t_activities (label, description, active)
VALUES 
('Expertise Papillons','Financement lié aux activités d''expertise entomologiques',true),
('Pôle Invertébrés & ORB', 'Financement lié à l''animation du Pôle Invertébrés ou de l''Observatoire Régional de la Biodiversité', true),
('Bénévolat', 'Financement lié aux activités bénévoles de la structure',true);

-- Intégrer la notion d'activité aux budgets
ALTER TABLE comptasso.t_budgets ADD COLUMN id_activity integer;

ALTER TABLE comptasso.t_budgets
ADD CONSTRAINT fk_t_budgets_id_activity FOREIGN KEY (id_activity) 
REFERENCES comptasso.t_activities(id_activity) ON UPDATE CASCADE;

CREATE VIEW comptasso.v_synthese_activities AS (
SELECT 
	a.id_activity,
	a.label,
	a.description,
	a.active,
	sum(COALESCE(b.budget_amount, 0::numeric)::numeric(8,2) - comptasso.get_sum_movement(b.id_budget, 'Recette'::text)) AS to_receive, -- to receive amount
	sum(COALESCE(b.budget_amount, 0::numeric)::numeric(8,2)) AS global_amount, -- total amounts
	b1.count AS active_budgets,
	b2.count AS inactive_budgets,
FROM comptasso.t_activities a
LEFT JOIN comptasso.t_budgets b ON b.id_activity=a.id_activity
LEFT JOIN LATERAL ( SELECT count(*)
            FROM comptasso.t_budgets
            WHERE v_1.uuid_attached_row = s.unique_id_sinp
            GROUP BY id_activity
            LIMIT 1) b1 ON true
GROUP BY a.id_activity, a.label, a.description, a.active
);

DROP VIEW comptasso.v_budgets;

CREATE OR REPLACE VIEW comptasso.v_budgets
AS SELECT b.id_budget,
    b.name,
    b.reference,
    f.id_funder,
    f.name AS funder,
    bt.label AS type_budget,
    a.label AS activity,
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
   	 LEFT JOIN comptasso.t_activities a ON b.id_activity = a.id_activity
     LEFT JOIN comptasso.dict_budget_types bt ON b.id_type_budget = bt.id_type_budget
     LEFT JOIN comptasso.t_funders f ON f.id_funder = b.id_funder
     LEFT JOIN comptasso.t_operations op ON op.id_budget = b.id_budget
     LEFT JOIN comptasso.cor_action_budget cab ON cab.id_budget = b.id_budget
  GROUP BY b.id_budget, b.name, b.reference, f.id_funder, f.name, bt.label, a.label, b.date_max_expenditure, b.date_return, b.budget_amount, b.payroll_limit, b.indirect_charges, b.comment, b.active, (comptasso.get_sum_movement(b.id_budget, 'Recette'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Recette'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (b.budget_amount - (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) + comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)))
  ORDER BY b.active DESC, b.name;