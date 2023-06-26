# Enter a python3 interpreter. Then do this:
# exec(open('linespector.py').read())
# And try, line by line, the commented out code at the end.

# Wonderful reference:
# https://cosmocode.io/how-to-connect-selenium-to-an-existing-browser-that-was-opened-manually/
# ( found from here: https://stackoverflow.com/a/70088095 )

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import copy, re, base64, magic

try: G
except NameError: G = {}
# a bag for all global variables

def init():
    global G
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    chrome_driver = '/usr/bin/chromedriver'
    G['driver'] = webdriver.Chrome(chrome_driver, options=chrome_options)
    # print(G['driver'].title)
    # mime = magic.Magic(mime=True)
    G['all_tabs'] = {}
    for handle in G['driver'].window_handles:
        G['driver'].switch_to.window(handle)
        G['all_tabs'][G['driver'].title] = handle
    G['driver'].switch_to.window(G['all_tabs']['LINE'])

def refresh_chat():
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
        item = { 'time_stamp': datetime.fromtimestamp(int(msg['data-timestamp'])//1000) }
        if 'messageDate-module__date_wrap__I4ily' in msg['class']:
            item['type'] = '日期'
            item['text'] = msg['data-message-content']
        elif 'systemMessage-module__message__yIiOJ' in msg['class']:
            item['type'] = '系統'
            item['text'] = msg['data-message-content']
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
                item['uname'] = to_del.text
                to_del.replaceWith('')
            else:
                item['uname'] = '*'
            if 'data-message-content' in msg.attrs:
                item['type'] = msg['data-message-content']
                item['html'] = msg.prettify()
                img = msg.find('img')
                if img:
                    blob= img['src']
                    m = re.search(r'/([\w-]{30,})$', blob)
                    if m is not None:
                        item['src'] = '{}/{}.jpg'.format(ts2path(item['time_stamp']), m.group(1))
                        save_blob_as(blob, item['src'])
                if not 'src' in item: item['src'] = ''
            else:
                item['type'] = '文字'
                item['text'] = msg.text
        else:
            item['type'] = 'unknown'
            item['html'] = msg.prettify()
        parsed_msgs.append(item)
    return parsed_msgs

def print_parsed(parsed_msgs, last_time_stamp=datetime.fromtimestamp(0)):
    for msg in parsed_msgs:
        if msg['time_stamp'] < last_time_stamp:
            continue
        if 'uname' in msg:
            print('{} [{}] {}'.format(msg['time_stamp'].strftime('%H:%M'), msg['uname'], msg['text']))
        else:
            print('==', msg['text'])

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

def save_blob_as(blob, filepath):
    with open(filepath, 'wb') as f:
        blob_content = get_file_content_chrome(G['driver'], blob)
        # print(magic.from_buffer(blob_content))
        # https://github.com/ahupp/python-magic
        f.write(blob_content)

def save_all_blobs(chat, path):
    images = chat.find_all('img')
    for img in images:
        blob = img['src']
        m = re.search(r'/([\w-]{30,})$', blob)
        if m is not None:
            save_blob_as(blob, '{}/{}.jpg'.format(path, m.group(1)))


'''
init()
parsed_msgs = refresh_chat()
print_parsed(parsed_msgs)
# After every switch to a new chat:
save_all_blobs(current_chat[0], '/tmp/linespector')
'''
