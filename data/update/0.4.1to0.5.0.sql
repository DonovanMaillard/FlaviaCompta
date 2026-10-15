DROP VIEW IF EXISTS comptasso.v_result_by_year;

CREATE VIEW comptasso.v_result_by_year AS (
WITH years AS (
	SELECT generate_series(min(EXTRACT('year' FROM op.effective_date))::integer,max(EXTRACT('year' FROM op.effective_date))::integer) AS year
	FROM comptasso.t_operations op
),
details AS (
	SELECT DISTINCT 
	y.YEAR,
	typ.LABEL AS type_category,
	cat.LEVEL AS level,
	cat.cd_category::TEXT AS cd_category,
	cat.cd_category||'. '||cat.LABEL AS label,
	cat.cd_broader,
	sum(op.amount) AS sum,
	jsonb_build_object('category',cat.cd_category||'. '||cat.LABEL,'result',sum(op.amount)) AS json
FROM comptasso.dict_categories cat
JOIN comptasso.dict_operation_types typ ON cat.id_type_operation = typ.id_type_operation
CROSS JOIN years y
LEFT JOIN LATERAL (
	SELECT * 
	FROM comptasso.t_operations op
	JOIN comptasso.dict_operation_types typ ON op.id_type_operation = typ.id_type_operation 
	WHERE EXTRACT('year' FROM op.effective_date)::integer=y.YEAR::integer
	AND op.id_category = cat.id_category 
	) op ON TRUE
WHERE typ.LABEL IN ('Recette','Dépense')
GROUP BY 1,2,3,4,5,6
ORDER BY 1,2,4,5
)
SELECT DISTINCT 
	d.YEAR AS year,
	d.type_category AS type_category,
	d.cd_category AS cd_category,
	d.LABEL AS label,
	jsonb_agg(child.json) AS json,
	COALESCE(sum(child.sum),0) AS amount
FROM details d
JOIN details child ON d.cd_category::text=child.cd_broader::text
WHERE d.LEVEL=1 AND child.YEAR=d.year
GROUP BY 1,2,3,4
);


DROP VIEW IF EXISTS comptasso.v_operations;

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
    dpm.label AS payment_method,
    op.id_account,
    ac.name AS account_name,
    ac.is_personnal AS personnal_account,
    op.id_budget,
    b.name AS budget_name,
    (cat.cd_category || '. '::text) || cat.label::text AS category,
    (cat2.cd_category || '. '::text) || cat2.label::text AS parent_category,
    op.uploaded_file,
    op.pointed,
    op.meta_create_date AS meta_create_date,
    op.meta_update_date
   FROM comptasso.t_operations op
     LEFT JOIN comptasso.dict_operation_types dot ON dot.id_type_operation = op.id_type_operation
     LEFT JOIN comptasso.dict_payment_methods dpm ON dpm.id_payment_method = op.id_payment_method
     LEFT JOIN comptasso.t_accounts ac ON ac.id_account = op.id_account
     LEFT JOIN comptasso.t_budgets b ON b.id_budget = op.id_budget
     LEFT JOIN comptasso.dict_categories cat ON cat.id_category = op.id_category
     LEFT JOIN comptasso.dict_categories cat2 ON cat.cd_broader = cat2.cd_category
  ORDER BY op.effective_date;

DROP TABLE IF EXISTS comptasso.dict_kilometric_scale;