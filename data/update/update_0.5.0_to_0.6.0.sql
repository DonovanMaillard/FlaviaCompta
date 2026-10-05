-- Retirer la notion de coût fixe
ALTER TABLE comptasso.t_budgets DROP COLUMN allowed_fixed_cost;
ALTER TABLE comptasso.t_budgets ADD COLUMN profit_bonus boolean NOT NULL DEFAULT FALSE;

-- Retirer le coût fixe de la correspondance budget/salarié
ALTER TABLE comptasso.cor_payroll_budget DROP COLUMN fixed_cost;

CREATE OR REPLACE VIEW comptasso.v_decode_payroll_budgets
AS SELECT cpb.id_payroll_budget,
    p.id_payroll,
    cpb.id_budget,
    b.name AS budget_name,
    cpb.nb_days_allocated
    FROM comptasso.cor_payroll_budget cpb
     LEFT JOIN comptasso.t_payrolls p ON cpb.id_payroll = p.id_payroll
     LEFT JOIN comptasso.t_budgets b ON cpb.id_budget = b.id_budget;

DROP VIEW IF EXISTS comptasso.v_synthese_payroll_budget;

CREATE VIEW comptasso.v_synthese_payroll_budget AS
SELECT
    g.id_member,
    g.member_name,
    g.id_budget,
    g.name,
    gp.date_min_period,
    gp.date_max_period,
    gp.total_gross_remuneration,
    gp.total_employer_charges,
    gp.total_work_days,
    g.allocated_days,
    round(gp.total_gross_remuneration / gp.total_work_days, 2) * g.allocated_days AS justified_remuneration,
    round(gp.total_employer_charges   / gp.total_work_days, 2) * g.allocated_days AS justified_charges,
    (round(gp.total_gross_remuneration / gp.total_work_days, 2)
   + round(gp.total_employer_charges   / gp.total_work_days, 2)) * g.allocated_days AS justified_payroll
FROM (
    SELECT p.id_member, m.member_name, cpb.id_budget, b.name,
           sum(cpb.nb_days_allocated) AS allocated_days
    FROM comptasso.cor_payroll_budget cpb
    LEFT JOIN comptasso.t_payrolls p ON cpb.id_payroll = p.id_payroll
    LEFT JOIN comptasso.t_budgets  b ON b.id_budget   = cpb.id_budget
    LEFT JOIN comptasso.t_members  m ON m.id_member   = p.id_member
    GROUP BY p.id_member, m.member_name, cpb.id_budget, b.name
) g
CROSS JOIN LATERAL (
    SELECT min(x.date_min_period)          AS date_min_period,
           max(x.date_max_period)          AS date_max_period,
           sum(x.total_gross_remuneration) AS total_gross_remuneration,
           sum(x.employer_charge_amount)   AS total_employer_charges,
           sum(x.worked_days)              AS total_work_days
    FROM comptasso.get_payrolls(g.id_member, g.id_budget) x
) gp;


-- Ajout d'un champs jsonb pour stocker "temporairement" l'allocation du budget à chaque salarié avant cloture
ALTER TABLE comptasso.t_budgets ADD COLUMN draft_allocations jsonb;

-- Ajout d'un champs date de cloture sur la table budget, qui remplacera le booleen active
ALTER TABLE comptasso.t_budgets ADD COLUMN date_closing date;

-- Calculer une date de cloture pour tous les budgets inactifs
UPDATE comptasso.t_budgets b
SET date_closing = COALESCE(
        (SELECT max(op.effective_date)
         FROM comptasso.t_operations op
         WHERE op.id_budget = b.id_budget),
        now()
    )::date
WHERE NOT b.active
  AND b.date_closing IS NULL;

-- Retirer la notion de "Actif" : remplacée par la notion de cloture 
ALTER TABLE comptasso.t_budgets DROM COLUMN active;


-- Actualiser la vue correspondante
DROP VIEW IF EXISTS comptasso.v_budgets;

CREATE OR REPLACE VIEW comptasso.v_budgets AS
SELECT b.id_budget,
    b.name,
    b.reference,
    f.id_funder,
    f.name AS funder,
    bt.label AS type_budget,
    a.label AS activity,
    COALESCE(b.date_max_expenditure::text, '-') AS date_max_expenditure,
    COALESCE(b.date_return::text, '-') AS date_return,
    COALESCE(b.budget_amount, 0)::numeric(8,2) AS budget_amount,
    COALESCE(b.payroll_limit, 0)::numeric(8,2) AS payroll_limit,
    COALESCE(b.indirect_charges, 0)::numeric(8,2) AS indirect_charges,
    COALESCE(b.indirect_charges / 100 * b.payroll_limit, 0)::numeric(8,2) AS indirect_charges_amount,
    b.comment,
    mv.received_amount,
    (mv.received_amount / NULLIF(b.budget_amount, 0) * 100)::numeric(8,2) AS percent_received,
    mv.spent_amount,
    (mv.spent_amount / NULLIF(b.budget_amount, 0) * 100)::numeric(8,2) AS percent_spent,
    mv.committed_amount,
    (mv.committed_amount / NULLIF(b.budget_amount, 0) * 100)::numeric(8,2) AS percent_committed,
    COALESCE(b.budget_amount, 0) - (mv.spent_amount + mv.committed_amount) AS available_amount,
    COALESCE(ops.last_operation::text, '-') AS last_operation,
    COALESCE(acts.last_action_date::text, '-') AS last_action_date,
    ops.nb_operations,
    b.profit_bonus,
    b.draft_allocations,
    b.date_closing
FROM comptasso.t_budgets b
LEFT JOIN comptasso.t_activities a ON a.id_activity = b.id_activity
LEFT JOIN comptasso.dict_budget_types bt ON bt.id_type_budget = b.id_type_budget
LEFT JOIN comptasso.t_funders f ON f.id_funder = b.id_funder
CROSS JOIN LATERAL (
    SELECT comptasso.get_sum_movement(b.id_budget, 'Recette')    AS received_amount,
           comptasso.get_sum_movement(b.id_budget, 'Dépense')    AS spent_amount,
           comptasso.get_sum_movement(b.id_budget, 'Engagement') AS committed_amount
) mv
CROSS JOIN LATERAL (
    SELECT max(op.effective_date) AS last_operation,
           count(*)               AS nb_operations
    FROM comptasso.t_operations op
    WHERE op.id_budget = b.id_budget
) ops
CROSS JOIN LATERAL (
    SELECT max(cab.date_action) AS last_action_date
    FROM comptasso.cor_action_budget cab
    WHERE cab.id_budget = b.id_budget
) acts;

-- Table de stockage des intéressements acquis par salarié
CREATE TABLE comptasso.t_profit_bonus (
	id_pb serial PRIMARY KEY,
	id_budget integer NOT NULL,
	id_member integer NOT NULL,
	allocated_amount numeric(12,2) NOT NULL,
	profit_percent numeric(5,2) NOT NULL,
	profit_bonus_amount numeric(12,2),
	meta_create_date timestamp without time zone,
	meta_update_date timestamp without time zone,
);

-- Ajouter les clés étrangères sur id_budget, id_member

CREATE TRIGGER tri_meta_dates_change_t_funders
BEFORE INSERT OR UPDATE ON comptasso.t_profit_bonus 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

-- Vue décode de l'intéressement
CREATE OR REPLACE VIEW comptasso.v_profit_bonus 
AS SELECT
    pb.id_pb,
    pb.id_budget,
    b.name, 
    b.budget_amount,
    comptasso.get_sum_movement(b.id_budget, 'Recette') AS received_amount,
    b.date_closing,
    pb.id_member,
    m.member_name,
    pb.allocated_amount,
    pb.profit_percent,
    pb.profit_bonus_amount,
    pb.meta_create_date,
    pb.meta_update_date
FROM comptasso.t_profit_bonus pb
LEFT JOIN comptasso.t_budgets b ON pb.id_budget=b.id_budget
LEFT JOIN comptasso.t_members m ON pb.id_member=m.id_member;