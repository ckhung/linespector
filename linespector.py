# python3 linespector.py -h
# mkdir ~/linespector
# # use sqlite3 to create a db ~/linespector/pub_group_chat.sqlite3
# python3 linespector.py ~/linespector/pub_group_chat.sqlite3
#
# To debug:
# python3 -i linespector.py -m ''
# Then inside the python3 interpreter:
# >>> init()
# >>> parsed_msgs = parse_chat(save=True)
# After every code update:
# >>> sys.argv[1:] = ['-m', '', 'pub_group_chat.sqlite3']
# >>> exec(open('linespector.py').read())
# >>> parsed_msgs = parse_chat(save=True)
# pretty print page for debugging:
# >>> print(G['page_soup'].prettify())

# Wonderful reference:
# https://cosmocode.io/how-to-connect-selenium-to-an-existing-browser-that-was-opened-manually/
# ( found from here: https://stackoverflow.com/a/70088095 )

import argparse, os, sqlite3, copy, re, base64, magic, sys
from warnings import warn
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from datetime import datetime

try: G
except NameError: G = {}
# a bag for all global variables

def init():
    global G
    chrome_options = Options()
    chrome_options.add_experimental_option('debuggerAddress', '127.0.0.1:'+str(G['args'].port))
    service = Service(executable_path='/usr/bin/chromedriver')
    G['driver'] = webdriver.Chrome(options=chrome_options, service=service)
    # print(G['driver'].title)
    # mime = magic.Magic(mime=True)
    G['all_tabs'] = {}
    for handle in G['driver'].window_handles:
        G['driver'].switch_to.window(handle)
        G['all_tabs'][G['driver'].title] = handle
    G['driver'].switch_to.window(G['all_tabs']['LINE'])

def parse_chat(save=False):
    global G
    G['page_soup'] = BeautifulSoup(G['driver'].page_source, 'html.parser')
    # with open('/tmp/linespector.html', 'w') as f: f.write(G['page_soup'].prettify())
    G['all_chats'] = G['page_soup'].find_all('div', {'class': 'chatlistItem-module__chatlist_item__MOwxh'})
    current_chat_title = G['page_soup'].find('button', {'class': 'chatroomHeader-module__button_name__US7lb'}).text
    current_chat_content = G['page_soup'].find_all('div', {'class': 'message_list'})
    match = re.match(r'(.*)\((\d+)\)', current_chat_title)
    if match:
        current_chat_title = match.group(1)
        group_size = match.group(2)
    else:
        group_size = 2
    current_chat_content = G['page_soup'].find_all('div', {'class': 'message_list'})
    assert 1==len(current_chat_content)
    msg_list = current_chat_content[0].find_all('div', {'data-timestamp':True})[::-1]
    G['msg_list'] = msg_list
    parsed_msgs = []
    for msg0 in msg_list:
        msg = copy.copy(msg0) # try to be non-destructive to G['page_soup']
        # msg = msg0 # destructive!
        item = {
            'time_stamp': int(msg['data-timestamp'])//1000,
            # 'time_stamp': datetime.fromtimestamp(int(msg['data-timestamp'])//1000)
            'chat_title': current_chat_title,
            'group_size': group_size,
            'msg_type': '',
            'user_name': '*',
            'prefix': '',
            'msg_content': '',
            'img_id': '',
            'html': '',
        }
        if 'messageDate-module__date_wrap__I4ily' in msg['class']:
            item['msg_type'] = '日期'
            item['msg_content'] = msg['data-message-content']
        elif 'systemMessage-module__message__yIiOJ' in msg['class']:
            item['msg_type'] = '系統'
            item['msg_content'] = msg['data-message-content']
        elif 'data-message-content-prefix' in msg.attrs:
            item['prefix'] = msg['data-message-content-prefix'].strip()
            to_del = msg.find('span', {'class': 'metaInfo-module__read_count__8-U6j'})
            if to_del: to_del.replaceWith('')
            to_del = msg.find('button')
            if to_del: to_del.replaceWith('')
            to_del = msg.find('time')
            if to_del: to_del.replaceWith('')
            to_del = msg.find('pre', {'class': 'username-module__username__vGQGj'})
            if to_del:
                item['user_name'] = to_del.text
                to_del.replaceWith('')
            if 'data-message-content' in msg.attrs:
                item['msg_type'] = msg['data-message-content']
                img = msg.find('img')
                if item['msg_type'] in ['圖片', '影片']:
                    item['msg_content'] = img['src']
                    item['img_id'] = blob_id(img['src'])
                elif item['msg_type'] == '貼圖':
                    item['msg_content'] = img['src']
                else:
                    item['html'] = msg.prettify()
            else:
                item['msg_type'] = '文字'
                to_del = msg.find('div', {'class': 'replyMessageContent-module__message__0FNkK'})
                if to_del:
                    to_del.replaceWith('')
                item['msg_content'] = msg.text
        else:
            item['msg_type'] = 'unknown'
            item['html'] = msg.prettify()
        parsed_msgs.append(item)
        if save:
            if item['img_id'] != '':
                save_blob_to_sqlite3(G['sqlite3'], item['msg_content'])
            save_message_to_sqlite3(G['sqlite3'], item)
    return parsed_msgs

def print_parsed(parsed_msgs, last_time_stamp=datetime.fromtimestamp(0)):
    for msg in parsed_msgs:
        if msg['time_stamp'] < last_time_stamp:
            continue
        if 'user_name' in msg:
            print('{} [{}] {}'.format(msg['time_stamp'].strftime('%H:%M'), msg['user_name'], msg['msg_content']))
        else:
            print('==', msg['msg_content'])

# https://stackoverflow.com/a/47425305
def get_file_content_chrome(driver, uri):
  result = driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
    """, uri)
  if type(result) == int :
    raise Exception("Request failed with status %s" % result)
  return base64.b64decode(result)

def blob_id(blob):
    m = re.search(r'/([\w-]{36})$', blob)
    return m.group(1) if m else ''

def save_blob_to_sqlite3(sqcon, blob):
    cursor = sqcon.cursor()
    cursor.execute(
        'insert or replace into images (id, img_content) values (?, ?)',
        (blob_id(blob), get_file_content_chrome(G['driver'], blob))
    )
    sqcon.commit()
    cursor.close()

def save_message_to_sqlite3(sqcon, item):
    cursor = sqcon.cursor()
    cursor.execute(
        'insert or replace into messages (time_stamp, chat_title, group_size, msg_type, user_name, prefix, msg_content, img_id, html) values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [ item[x] for x in ['time_stamp', 'chat_title', 'group_size', 'msg_type', 'user_name', 'prefix', 'msg_content', 'img_id', 'html'] ]
    )
    sqcon.commit()
    cursor.close()

#def save_blob_as_file(filepath, blob):
#    with open(filepath, 'wb') as f:
#        blob_content = get_file_content_chrome(G['driver'], blob)
#        # print(magic.from_buffer(blob_content))
#        # https://github.com/ahupp/python-magic
#        f.write(blob_content)

#def save_all_blobs(chat, path):
#    images = chat.find_all('img')
#    for img in images:
#        blob = img['src']
#        m = re.search(r'/([\w-]{30,})$', blob)
#        if m is not None:
#            save_blob_as_file('{}/{}.jpg'.format(path, m.group(1)), blob)


# save_all_blobs(current_chat_content[0], '/tmp/linespector')

parser = argparse.ArgumentParser(
    description='line inspector',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-p', '--port', type=int, default=9222,
    help='chrome debug port')
parser.add_argument('-t', '--topdir', type=str,
    default=os.environ['HOME']+'/linespector',
    help='top directory for the db file if its full path is not specified')
parser.add_argument('-m', '--mode', type=str, default='init+parse+save',
    help='save? parse? or init only?')
parser.add_argument('dbfile', help='sqlite3 storage file')
G['args'] = parser.parse_args()
if not os.path.isabs(G['args'].dbfile):
    G['args'].dbfile = G['args'].topdir + '/' + G['args'].dbfile

if 'init' in G['args'].mode: init()
G['sqlite3'] = sqlite3.connect(G['args'].dbfile)
if 'parse' in G['args'].mode:
    parsed_msgs = parse_chat( save='save' in G['args'].mode )

G['sqlite3'].close()

