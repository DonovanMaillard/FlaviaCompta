-- Ajouter un champs pour le fichier uploadés dans la table des masses salariales
ALTER TABLE comptasso.t_payrolls ADD COLUMN uploaded_file varchar(255);