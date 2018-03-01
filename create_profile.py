#!/usr/bin/env python
#aikipooh@gmail.com

from configparser import ConfigParser
from shutil import copytree
from os import path
from csv import DictReader

accounts=[]
with open('100 Gmail.csv') as f:
    rd=DictReader(f)
    accounts.extend(rd)
    
#basepath=environ.get('BASEPATH')
# '/home/pooh/.mozilla/firefox/'
basepath=path.expanduser('~')+'/.mozilla/firefox/'

profiles_fn=basepath+'profiles.ini'

config = ConfigParser()
config.optionxform=str # Leave it case-sensitive
with open(profiles_fn) as f: config.read_file(f)

last_profile=config.sections()[-1] # ProfileXX
last_profile_num=int(last_profile[7:])

pooh = '/pooh/' in basepath

if pooh:
    path=config['Profile1']['Path'] # First one is too fat
else:
    path=config['Profile0']['Path']
print('Copying: '+path)

# We'll take Profile0 and clone to as many of them as needed
for num, val in enumerate(accounts[2:], last_profile_num+1):
    name=val['Email'].split('@')[0]
    print('Handling '+name)
    copytree(basepath+path, basepath+name)
    config['Profile{}'.format(num)]={
        'Name': name, 'IsRelative': 1, 'Path': name
    }
    # Now need to update proxy setting to the respective one in this profile
    # (prefs.js)
    if pooh: val['Proxy']='127.0.0.1:9000' # Testing only
    proxy_parsed=val['Proxy'].split(':')
    with open(basepath+name+'/prefs.js', 'a') as f:
        f.write('''
user_pref("network.proxy.http", "{0[0]}");
user_pref("network.proxy.http_port", {0[1]});
user_pref("network.proxy.share_proxy_settings", true);
user_pref("network.proxy.ssl", "{0[0]}");
user_pref("network.proxy.ssl_port", {0[1]});
user_pref("network.proxy.type", 1);
user_pref("network.proxy.no_proxies_on", "localhost, 127.0.0.1, www.supremenewyork.com, kith.com, packershoes.com");
        '''.format(proxy_parsed))
    
# from sys import stdout
# config.write(stdout)
with open(profiles_fn, 'w') as f: config.write(f, False)
