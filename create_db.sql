create table images (id text primary key, img_content blob);
create table messages (
    time_stamp int primary key,
    msg_type text,
    user_name text,
    prefix text,
    msg_content text,
    img_id text,
    html text,
    foreign key (img_id) references images(id)
);
create view messages_with_images as select * from messages left join images on messages.img_id=images.id;
-- PRAGMA table_info(messages_with_images)
