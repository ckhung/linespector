create table images (id text primary key, content blob);
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
