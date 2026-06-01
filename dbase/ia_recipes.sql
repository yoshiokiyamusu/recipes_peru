USE zau1dw9gx8qcfum4;

Select * from tt_recipes_tb;







-- ## Create a mysql table ## --

INSERT INTO tt_recipes_tb (id_recipe, name, description, prep_time, created_at)
VALUES (101, 'Spaghetti Carbonara', 'A classic Roman pasta dish made with eggs, hard cheese, cured pork, and black pepper.', '20 minutes', '2026-05-31');

CREATE TABLE tt_recipes_tb (

 row_id int(11) NOT NULL AUTO_INCREMENT,
 id_recipe int(11) NOT NULL,
 name varchar(25) NOT NULL,
 description varchar(250) NOT NULL,
 prep_time varchar(25) NOT NULL,
 created_at DATE NOT NULL,
 PRIMARY KEY (row_id)
);

