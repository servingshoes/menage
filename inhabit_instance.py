#!/usr/bin/env python
#pooh@aikipooh.name

# Create instance with desktop environment, deploy up to date tool probably from git and run the tool.
# The workflow is the following
# 1. Create all the instances from the input file
# 2. Ask AWS for the credentials. Wait until they're available for everyone.
# 3. Connect by ssh, copy the files and run the init_instance script

from pdb import set_trace
from logging import basicConfig, DEBUG, INFO, WARNING, ERROR, getLogger
from csv import DictReader, DictWriter
from subprocess import run, PIPE

from retrying import retry

from create_instance import instance_manager

ll=WARNING
ll=INFO
ll=DEBUG
basicConfig(format='{asctime} {threadName:11s}: {message}', datefmt="%H:%M:%S",
            style='{', level=ll)
lg=getLogger(__name__)

# Parameters used to run simulate.py / simulate_ubuntu.py
result_fn='result.csv'
instance_fn='instances.csv'
config_fn='100 Gmail.csv'
config_fn='1.csv'

profile='henryaws' # Profile to use for AWS work

########## No configuration past this line ###############

# instance_manager's by profiles

# Warming up
manager=instance_manager()

# Here we'll store initial lines updated with the instance id
result=[]

# All profiles from the the input file to iterate by when getting credentials
all_profiles=set()

# Actual work
if 1:
    with open(config_fn) as fi:
        rd=DictReader(fi)
        for i in list(rd)[:1]:
            # Now create this instance
            # args={'new': i['isnew'] == 'Y', 'ostype': i['OS'],
            #       'type': i['insttype']}
            args={'new': False, 'ostype': 'LU', 'type': 'medium'}
            
            res=manager.create_multi_instances(profile, args)
            i['instance_id']=res[0]['instance_id']
            result.append(i)

    fieldnames=rd.fieldnames
    if 'instance_id' not in fieldnames: fieldnames.append('instance_id')
    # Rewrite the initial file, updating with instance_id
    with open(config_fn, 'w') as fo:
        wr=DictWriter(fo, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(result)

# with open(instance_fn) as fi:
#     public_ips={_['instance_id']: _['public_ip'] for _ in DictReader(fi)}

lg.info('Right after creation: {}'.format(manager.all_ready()))
for profile in all_profiles:
    manager.decrypt_ec2_secure_info(profile)

if not manager.all_ready():
    lg.error('Some instances are not ready yet. Investigate!')
    del manager
    exit(1)

exit()

def retry_exc(e):
    set_trace()
    # self, *args=e.args
    # e.args=args # In case we'll reraise

    # elif isinstance(e, TimeoutException): # Let's try our luck again
    #     #with open('bad.html', 'w') as fo: fo.write(self.driver.page_source)
    #     lg.warning('Retrying after timeout')
    # elif isinstance(e, WebDriverException):
    #     lg.exception('Driver problem')

    lg.exception('retry_exc: {}')

    return True


# Now wait for everyone to be fully initialised and copy the files
@retry(wait_fixed=10000, retry_on_exception=retry_exc)
def runcmd(cmd):
    lg.info('Running: '+cmd)

    cp = run(cmd,
               #stdin=PIPE,
               stdout=PIPE, stderr=PIPE,
               check=True, shell=True)
    # outs, errs = proc.communicate(
    # #    input=bytes(d['base64Data'], 'utf-8')
    # )
    # Returns CompletedProcess
    lg.debug('------------- STDOUT ---------------')
    lg.debug(cp.stdout.decode())
    lg.debug('------------- STDERR ---------------')
    lg.debug(cp.stderr.decode())

#cur_iid='i-084f6fa6cef25e47f' # Arch new
#cur_iid='i-05af75f8f82964b1c' # Ubuntu new
with open(config_fn) as fi:
    rd=DictReader(fi)
    for i in rd:
        # Testing only
        #if i['instance_id'] != cur_iid: continue

        inst=manager.get_instance(i['instance_id'])

        if i['OS'] == 'LA': # Need to modify sshd_config to allow X11 forwarding
            host='root@{}'.format(inst['public_ip'])

            cmd='scp -i KEY_FILES/SimulatorNew.pem -o StrictHostKeyChecking=no init_arch_1.sh {}:'.format(host)
            runcmd(cmd)

            # Now we'll have X11 forwarding
            cmd='ssh -i KEY_FILES/SimulatorNew.pem {} ./init_arch_1.sh'.format(host)
            runcmd(cmd)
        elif i['OS'] == 'LU':
            host='ubuntu@{}'.format(inst['public_ip'])

        lg.info('Copying init_instance.sh')
        cmd='scp -i KEY_FILES/SimulatorNew.pem -o StrictHostKeyChecking=no init_instance.sh {}:'.format(host)
        runcmd(cmd)

        # TODO: Copy the configuration parameters to the new instance
        
        lg.info('Running init_instance.sh')
        # Need X forwarding
        cmd='ssh -Yi KEY_FILES/SimulatorNew.pem {} ./init_instance.sh'.format(host)
        runcmd(cmd)
    
del manager
