-- Add activities
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
            WHERE active
            GROUP BY id_activity) b1 ON b1.id_activity=a.id_activity
LEFT JOIN LATERAL ( SELECT count(*)
            FROM comptasso.t_budgets
            WHERE NOT active
            GROUP BY id_activity) b2 ON b1.id_activity=a.id_activity
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





# Work valuation and volunteering
DROP TABLE comptasso.cor_member_payroll;
DROP TABLE comptasso.cor_payroll_budget;
DROP TRIGGER tri_meta_dates_change_cor_member_payroll ON comptasso.cor_member_payroll ;
DROP TRIGGER tri_meta_dates_change_cor_payroll_budget ON comptasso.cor_payroll_budget;
DROP VIEW v_payroll_details;
DROP VIEW v_payrolls;

CREATE TABLE comptasso.t_work_value (
  id_work_value serial PRIMARY KEY,
  id_member integer NOT NULL,
  date_min_period date NOT NULL,
  date_max_period date NOT NULL,
  gross_remuneration numeric(8,2) NOT NULL,
  gross_premium numeric(8,2) NOT NULL,
  employer_charge_amount numeric(8,2) NOT NULL,
  volunteering_valuation numeric(8,2) NOT NULL,
  real_worked_days numeric(8,2) NOT NULL,
  meta_create_date timestamp WITHOUT time ZONE,
  meta_update_date timestamp WITHOUT time ZONE
);

CREATE TABLE comptasso.cor_work_budget (
  id_work_budget serial PRIMARY KEY,
  id_work_value integer NOT NULL,
  id_budget integer NOT NULL,
  nb_days_allocated numeric(8,2) NOT NULL,
  fixed_cost numeric(8,2),
  meta_create_date timestamp WITHOUT time ZONE,
  meta_update_date timestamp WITHOUT time ZONE
);

CREATE TRIGGER tri_meta_dates_change_t_work_value 
BEFORE INSERT OR UPDATE ON comptasso.t_work_value
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_cor_work_budget 
BEFORE INSERT OR UPDATE ON comptasso.cor_work_budget 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();


-- t_work_value
ALTER TABLE comptasso.t_work_value
ADD CONSTRAINT fk_t_work_value_id_member FOREIGN KEY (id_member) 
REFERENCES comptasso.t_members(id_member) ON UPDATE CASCADE;

-- cor_work_budget
ALTER TABLE comptasso.cor_work_budget
ADD CONSTRAINT fk_cor_work_budget_id_budget FOREIGN KEY (id_budget) 
REFERENCES comptasso.t_budgets(id_budget) ON UPDATE CASCADE;

ALTER TABLE comptasso.cor_work_budget
ADD CONSTRAINT fk_cor_work_budget_id_member FOREIGN KEY (id_member) 
REFERENCES comptasso.t_members(id_member) ON UPDATE CASCADE;



-- Mise en place des notes de frais
-- Retirer la contrainte NOT NULL sur le champs account_number de t_accounts (pour les notes de frais)
ALTER TABLE comptasso.t_accounts ALTER COLUMN account_number DROP NOT NULL;
