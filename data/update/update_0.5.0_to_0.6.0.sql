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

-- Ajout d'un champs date pour stocker la date de lancement du projet
ALTER TABLE comptasso.t_budgets ADD COLUMN date_start date;

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

-- Ajout d'une date de début du projet
ALTER TABLE comptasso.t_budgets ADD COLUMN date_start date;

-- Calculer une date de lancement pour les projets existants (1ere date entre la 1ere operation et la date d'écriture)
UPDATE comptasso.t_budgets b
SET date_start = LEAST(
    (SELECT min(op.effective_date)
     FROM comptasso.t_operations op
     WHERE op.id_budget = b.id_budget),
    b.meta_create_date::date
);

-- Actualiser la vue correspondante
DROP VIEW IF EXISTS comptasso.v_budgets;

CREATE OR REPLACE VIEW comptasso.v_budgets AS
SELECT b.id_budget,
    b.name,
    b.reference,
    f.id_funder,
    f.name AS funder,
    bt.id_type_budget AS id_type_budget,
    bt.label AS type_budget,
    a.id_activity AS id_activity,
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
    b.date_start,
    b.date_closing,
    b.meta_create_date,
    b.meta_update_date
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


-- Actualiser la vue de synthèse par activité
CREATE OR REPLACE VIEW comptasso.v_synthese_activities
AS SELECT a.id_activity,
    a.label,
    a.description,
    a.active,
    sum(COALESCE(b.budget_amount, 0::numeric)::numeric(8,2) - comptasso.get_sum_movement(b.id_budget, 'Recette'::text)) AS to_receive,
    sum(COALESCE(b.budget_amount, 0::numeric)::numeric(8,2)) AS global_amount,
    b1.count AS active_budgets,
    b2.count AS inactive_budgets
   FROM comptasso.t_activities a
     LEFT JOIN comptasso.t_budgets b ON b.id_activity = a.id_activity
     LEFT JOIN LATERAL ( SELECT count(*) AS count
           FROM comptasso.t_budgets
          WHERE t_budgets.date_closing IS NULL AND t_budgets.id_activity = a.id_activity
          GROUP BY t_budgets.id_activity) b1 ON true
     LEFT JOIN LATERAL ( SELECT count(*) AS count
           FROM comptasso.t_budgets
          WHERE t_budgets.date_closing IS NOT NULL AND t_budgets.id_activity = a.id_activity
          GROUP BY t_budgets.id_activity) b2 ON true
  GROUP BY a.id_activity, a.label, a.description, a.active, b1.count, b2.count;

-- Retirer la notion de "Actif" : remplacée par la notion de cloture 
ALTER TABLE comptasso.t_budgets DROP COLUMN active;

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
ALTER TABLE comptasso.t_profit_bonus ADD CONSTRAINT fk_profit_bonus_budget
FOREIGN KEY (id_budget) REFERENCES comptasso.t_budgets(id_budget);

ALTER TABLE comptasso.t_profit_bonus ADD CONSTRAINT fk_profit_bonus_member
FOREIGN KEY (id_member) REFERENCES comptasso.t_members(id_member);

-- Stocker les dates d'écriture et de modifications sur les intéressements
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


-- Permettre un commentaire plus long sur les opérations
-- En supprimant et recréant les vues dépendantes
DROP VIEW comptasso.v_result_by_year;
DROP VIEW comptasso.v_operations;

-- En changeant le type de champs
ALTER TABLE comptasso.t_operations
ALTER COLUMN detail_operation TYPE text USING detail_operation::text;

-- Puis reconstruire les vues dépendantes
CREATE OR REPLACE VIEW comptasso.v_result_by_year
AS WITH years AS (
         SELECT generate_series(min(date_part('year'::text, op.effective_date))::integer, max(date_part('year'::text, op.effective_date))::integer) AS year
           FROM comptasso.t_operations op
        ), details AS (
         SELECT DISTINCT y.year,
            typ.label AS type_category,
            cat.level,
            cat.cd_category::text AS cd_category,
            (cat.cd_category || '. '::text) || cat.label::text AS label,
            cat.cd_broader,
            sum(op.amount) AS sum,
            jsonb_build_object('category', (cat.cd_category || '. '::text) || cat.label::text, 'result', sum(op.amount)) AS json
           FROM comptasso.dict_categories cat
             JOIN comptasso.dict_operation_types typ ON cat.id_type_operation = typ.id_type_operation
             CROSS JOIN years y
             LEFT JOIN LATERAL ( SELECT op_1.id_operation,
                    op_1.id_grp_operation,
                    op_1.name,
                    op_1.detail_operation,
                    op_1.id_type_operation,
                    op_1.operation_date,
                    op_1.effective_date,
                    op_1.amount,
                    op_1.id_payment_method,
                    op_1.id_account,
                    op_1.id_budget,
                    op_1.id_category,
                    op_1.uploaded_file,
                    op_1.pointed,
                    op_1.meta_id_digitiser,
                    op_1.meta_create_date,
                    op_1.meta_update_date,
                    typ_1.id_type_operation,
                    typ_1.label,
                    typ_1.description,
                    typ_1.operator
                   FROM comptasso.t_operations op_1
                     JOIN comptasso.dict_operation_types typ_1 ON op_1.id_type_operation = typ_1.id_type_operation
                  WHERE date_part('year'::text, op_1.effective_date)::integer = y.year AND op_1.id_category = cat.id_category) op(id_operation, id_grp_operation, name, detail_operation, id_type_operation, operation_date, effective_date, amount, id_payment_method, id_account, id_budget, id_category, uploaded_file, pointed, meta_id_digitiser, meta_create_date, meta_update_date, id_type_operation_1, label, description, operator) ON true
          WHERE typ.label::text = ANY (ARRAY['Recette'::character varying, 'Dépense'::character varying]::text[])
          GROUP BY y.year, typ.label, cat.level, (cat.cd_category::text), ((cat.cd_category || '. '::text) || cat.label::text), cat.cd_broader
          ORDER BY y.year, typ.label, (cat.cd_category::text), ((cat.cd_category || '. '::text) || cat.label::text)
        )
 SELECT DISTINCT d.year,
    d.type_category,
    d.cd_category,
    d.label,
    jsonb_agg(child.json) AS json,
    sum(child.sum) AS amount
   FROM details d
     JOIN details child ON d.cd_category = child.cd_broader::text
  WHERE d.level = 1 AND child.year = d.year
  GROUP BY d.year, d.type_category, d.cd_category, d.label;


-- v_operations remontée plus tard, après intégration de la TVA
-- Retirer la notion de "pointé" inutilisée dans le même temps
ALTER TABLE comptasso.t_operations DROP COLUMN pointed ;

-- ARRETE ICI !!

-- Implémenter la gestion de la TVA --
-- Créer la table dict des modalités d'affectation des dépenses aux secteurs lucratifs/non lucratifs
CREATE TABLE comptasso.dict_vat_ratio (
    id_spending_allocation serial primary key,
    label varchar(50) NOT NULL,
    description text,
    ratio numeric(5,2) NOT NULL
);

INSERT INTO comptasso.dict_vat_ratio (label, description, ratio)
VALUES ('Secteur lucratif','Charge intégralement affectée au secteur lucratif et ouvrant droit à la récupération de TVA au taux de 100%.',1)
,('Essentiellement secteur lucratif','Charge essentiellement affectée au secteur lucratif et ouvrant droit à la récupération de TVA au taux de 90%.',0.90)
,('Mixte','Charge mixte affectée aux secteurs lucratif et non lucratif, ouvrant droit à la récupération de TVA au taux de 40%.',0.40)
,('Essentiellement secteur non lucratif','Charge essentiellement affectée au secteur non lucratif et ouvrant droit à la récupération de TVA au taux de 10%.',0.10)
,('Secteur non lucratif','Charge intégralement affectée au secteur non lucratif et n''ouvrant pas le droit à la récupération de TVA.',0)
;

-- Modifier la table t_operations
ALTER TABLE comptasso.t_operations ADD COLUMN invoice_reference varchar(50);
ALTER TABLE comptasso.t_operations ADD COLUMN vat_amount numeric(12,2);
ALTER TABLE comptasso.t_operations ADD COLUMN id_spending_allocation integer;
ALTER TABLE comptasso.t_operations ADD COLUMN vat_ratio numeric(5,2);
ALTER TABLE comptasso.t_operations ADD COLUMN recoverable_vat_amount numeric(12,2);
ALTER TABLE comptasso.t_operations ADD COLUMN with_depreciation boolean;

-- Ajouter une clé étrangère sur l'id de l'affectation TVA
ALTER TABLE comptasso.t_operations ADD CONSTRAINT fk_operation_vat_ratio
FOREIGN KEY (id_spending_allocation) REFERENCES comptasso.comptasso.dict_vat_ratio(id_spending_allocation);

-- Affecter toutes les dépenses existantes au secteur non lucratif sans récupération de TVA
UPDATE comptasso.t_operations
    SET id_spending_allocation=dict.id_spending_allocation,
    vat_ratio=dict.ratio,
    recoverable_vat_amount=0
FROM comptasso.dict_vat_ratio dict 
WHERE dict.label='Secteur non lucratif';


-- Remonter la vue v_operations intégrant les nouveaux champs
CREATE OR REPLACE VIEW comptasso.v_operations
AS SELECT op.id_operation,
    op.id_grp_operation,
    op.name AS name_operation,
    op.detail_operation,
    dot.id_type_operation,
    dot.label AS type_operation,
    op.operation_date,
    op.effective_date,
    date_part('year'::text, op.effective_date)::integer AS year,
    op.amount,
    op.vat_amount,
    op.id_spending_allocation,
    op.vat_ratio,
    op.recoverable_vat_amount,
    op.with_depreciation,
    dpm.label AS payment_method,
    op.id_account,
    ac.name AS account_name,
    ac.is_personnal AS personnal_account,
    op.id_budget,
    b.name AS budget_name,
    (cat.cd_category || '. '::text) || cat.label::text AS category,
    (cat2.cd_category || '. '::text) || cat2.label::text AS parent_category,
    op.invoice_reference,
    op.uploaded_file,
    op.meta_create_date,
    op.meta_update_date
   FROM comptasso.t_operations op
     LEFT JOIN comptasso.dict_operation_types dot ON dot.id_type_operation = op.id_type_operation
     LEFT JOIN comptasso.dict_payment_methods dpm ON dpm.id_payment_method = op.id_payment_method
     LEFT JOIN comptasso.t_accounts ac ON ac.id_account = op.id_account
     LEFT JOIN comptasso.t_budgets b ON b.id_budget = op.id_budget
     LEFT JOIN comptasso.dict_categories cat ON cat.id_category = op.id_category
     LEFT JOIN comptasso.dict_categories cat2 ON cat.cd_broader = cat2.cd_category
  ORDER BY op.effective_date;

