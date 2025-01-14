create database hotel;

use hotel;

show tables;

select * from auth_user;
select * from api_cartmodel;
insert into api_cartmodel (user_id,created_at,updated_at) values(1,"2024-12-22 14:27:28.866105","2024-12-22 14:27:28.866105");
select * from api_itemmodel;

select * from api_itemvariantmodel;
delete from api_itemmodel where id=6;
delete from api_itemvariantmodel where id=4;

select * from api_cartitemmodel;
delete from api_cartitemmodel where id=1;

select * from api_ordermodel;
select * from api_orderitemmodel;
