# Enter a python3 interpreter. Then do this:
# exec(open('linespector.py').read())
# And try, line by line, the commented out code at the end.

# Wonderful reference:
# https://cosmocode.io/how-to-connect-selenium-to-an-existing-browser-that-was-opened-manually/
# ( found from here: https://stackoverflow.com/a/70088095 )

import argparse, os, sqlite3, copy, re, base64, magic
from warnings import warn
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime

try: G
except NameError: G = {}
# a bag for all global variables

def init():
    global G
    chrome_options = Options()
    chrome_options.add_experimental_option('debuggerAddress', '127.0.0.1:'+str(G['args'].port))
    chrome_driver = '/usr/bin/chromedriver'
    G['driver'] = webdriver.Chrome(chrome_driver, options=chrome_options)
    # print(G['driver'].title)
    # mime = magic.Magic(mime=True)
    G['all_tabs'] = {}
    for handle in G['driver'].window_handles:
        G['driver'].switch_to.window(handle)
        G['all_tabs'][G['driver'].title] = handle
    G['driver'].switch_to.window(G['all_tabs']['LINE'])

def parse_chat(save=False):
    global G
    page_soup = BeautifulSoup(G['driver'].page_source, 'html.parser')
    # with open('a.htm', 'w') as f: f.write(page_soup.prettify())
    all_chats = page_soup.find_all('div', {'class': 'chatlistItem-module__chatlist_item__MOwxh'})
    current_chat = page_soup.find_all('div', {'class': 'message_list'})
    assert 1==len(current_chat)
    msg_list = current_chat[0].find_all('div', {'data-timestamp':True})[::-1]
    G['msg_list'] = msg_list
    parsed_msgs = []
    for msg0 in msg_list:
        msg = copy.copy(msg0) # try to be non-destructive to page_soup
        # msg = msg0 # destructive!
        item = {
            'time_stamp': int(msg['data-timestamp'])//1000,
            # 'time_stamp': datetime.fromtimestamp(int(msg['data-timestamp'])//1000)
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
                    warn(msg['data-timestamp'] + ': ' + item['msg_type'])
                    item['html'] = msg.prettify()
            else:
                item['msg_type'] = '文字'
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

def ts2path(ts):
    # timestamp to path
    return '/tmp/linespector'

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
        'insert or replace into images (id, content) values (?, ?)',
        (blob_id(blob), get_file_content_chrome(G['driver'], blob))
    )
    sqcon.commit()
    cursor.close()

def save_message_to_sqlite3(sqcon, item):
    cursor = sqcon.cursor()
    cursor.execute(
        'insert or replace into messages (time_stamp, msg_type, user_name, prefix, msg_content, img_id, html) values (?, ?, ?, ?, ?, ?, ?)',
        [ item[x] for x in ['time_stamp', 'msg_type', 'user_name', 'prefix', 'msg_content', 'img_id', 'html'] ]
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


# save_all_blobs(current_chat[0], '/tmp/linespector')

parser = argparse.ArgumentParser(
    description='line inspector',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-p', '--port', type=int, default=9222,
    help='chrome debug port')
parser.add_argument('-t', '--topdir', type=str,
    default=os.environ['HOME']+'/linespector',
    help='chrome debug port')
parser.add_argument('-m', '--mode', type=str, default='',
    help='save? parse? or init only?')
parser.add_argument('dbfile', help='sqlite3 storage file')
G['args'] = parser.parse_args()
if not os.path.isabs(G['args'].dbfile):
    G['args'].dbfile = G['args'].topdir + '/' + G['args'].dbfile

if 'init' in G['args'].mode: init()
G['sqlite3'] = sqlite3.connect(G['args'].dbfile)
if 'parse' in G['args'].mode:
    parsed_msgs = parse_chat( save='save' in G['args'].mode )

# G['sqlite3'].close()

# item['src'] = '{}/{}.jpg'.format(ts2path(item['time_stamp']), m.group(1))
#                if not 'src' in item: item['src'] = ''
