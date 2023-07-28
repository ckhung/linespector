# linespector
This project is for archiving messages of the "line" instant messaging app, which enjoys solid control over Taiwan's society. It contains two pieces of code:
- linespector.py can be used to save the currently open chat to a sqlite database
- index.php can be used to display the saved messages from the database

## Preparation

My desktop is linuxmint, debian edition. You may need to change the following commands if you are not using one of the GNU/linux distributions.
- Make sure you have either sqlite3 or litecli installed. I prefer the latter.
- Install selenium (and litecli):
  '''pip3 install selenium litecli```
- Execute create_db.sql in sqlite3 or litecli to create, say, line-chats.sqlite3 .

## Updating the database and display 

- Start chromium in debug mode:
  ```chromium --remote-debugging-port=9222```
- Start the line extension for chrome, log in, and switch to the chat you want to save. Then:
  ```python3 linespector.py line-chats.sqlite3```
- You can do this from sqlite or litecli to verify that the correct messages have been saved:
  ```select date(time_stamp, 'unixepoch'),chat_title,user_name,msg_type from messages```
- Edit config.php
- Visit index.php via apache2 with your browser
