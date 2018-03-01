#!/usr/bin/env python

"""
Create EC2 instances
"""

from boto3 import session # resource, client
from json import load, loads, dumps
from os import path
from contextlib import suppress
from sys import modules
from csv import DictReader, DictWriter
from argparse import ArgumentParser
from pdb import set_trace
from logging import basicConfig, DEBUG, INFO, WARNING, ERROR, getLogger
from base64 import b64decode

# try:
#     import Crypto
#     modules['Crypto'] = Crypto
#     from Crypto.Cipher import PKCS1_v1_5
#     from Crypto.PublicKey import RSA
# except:
#     import crypto
#     modules['Crypto'] = crypto
#     from crypto.Cipher import PKCS1_v1_5
#     from crypto.PublicKey import RSA

ll=WARNING
ll=INFO
ll=DEBUG
basicConfig(format='{asctime} {module}: {message}', datefmt="%H:%M:%S",
            style='{', level=ll)
lg=getLogger(__name__)

getLogger('botocore').setLevel(INFO)

class instance_manager:
    '''Handles a pool of sessions by profile'''
    
    instances_fn='instances.csv'
    amilist_fn='amilist.csv'

    def __init__(self):
        self.sessions={}
        
        # Instances to handle
        with open(self.instances_fn) as fi: self.instances=list(DictReader(fi))

        # AMI list:
        
        # Ubuntu AMIs
        # https://cloud-images.ubuntu.com/locator/ec2/

        with open(self.amilist_fn) as fi: self.amilist=list(DictReader(fi))

    def __del__(self):
        # Save instances information back to the file, overwriting the content
        with open(self.instances_fn, 'w', newline='') as fo:
            wr=DictWriter(fo, fieldnames=(
                'instance_id', 'type', 'winpwd', 'public_ip'))
            wr.writeheader()
            wr.writerows(self.instances)

    def get_session(self, profile):
        '''Get session by profile name. Create or return existing one.'''

        try:
            return self.sessions[profile]
        except KeyError:
            ses=session.Session(profile_name=profile)
            lg.debug('session: {}'.format(ses))
            self.sessions[profile]=ses
            return ses

    def get_instance(self, id):
        '''Get instance dict by id'''
        for i in self.instances:
            if i['instance_id'] == id: return i
        else:
            return None
        
    def create_key(self, profile):
        """
        Create the EC2 key file
        :return: 
        """
        ses=self.get_session(profile)

        with suppress(FileExistsError), \
             open('pooh.pem', 'x') as keyfile:
            #set_trace()
            key_pair = ses.resource('ec2').create_key_pair(KeyName='SimulatorNew')
            key_pair_out = str(key_pair.key_material)
            keyfile.write(key_pair_out)
            chmod(keyfile.fileno(), 0o0400) # So ssh won't complain        

    def decrypt(self, ciphertext, keyfile=path.expanduser('pooh.pem')):

        with open(keyfile) as inp:
            key = RSA.importKey(inp.read())

        cipher = PKCS1_v1_5.new(key)
        plaintext = cipher.decrypt(ciphertext, None)
        
        return plaintext

    def all_ready(self):
        '''Checks that all instances have credentials information'''
        # TODO: Maybe check winpwd here?
        return all(_.get('public_ip') for _ in self.instances)
            
    def decrypt_ec2_secure_info(self, profile):
        """
        Get windows password and save information to instances.csv file.
        """
        ses=self.get_session(profile)

        response = ses.client('ec2').describe_instances()
        # Get all the instances and search for the instance based on the provided Tag - Name
        for reservation in response["Reservations"]:
            for item in reservation["Instances"]:
                inst=self.get_instance(item["InstanceId"])
                if not inst: # Not ours
                    lg.debug('Skipping instance: {}'.format(item["InstanceId"]))
                    continue
                if inst.get('public_ip'): # Already set, no need to update
                    continue
                # Update with retrieved information
                inst.update({
                    'type': item['InstanceType'],
                    'public_ip': item['PublicIpAddress']})
        
    def create_multi_instances(self, profile, args, Key_Name="pooh", **kwargs):
        """
        Create multi instances with Testkey file.
        :param args: passed intact by argparser from command line
           ostype  - {LU, LA, W}, Ubuntu, arch or windows
           new     - [YN], is it the new image or not, Y - yes, N - no
        :return: 
        """
        lg.info('Creating an instance: {}'.format(args))
        
        ses=self.get_session(profile)
        # First find AMI by the args
        for i in self.amilist: # Find AMI to use by parameters
            if i['OS'] == args['ostype'] and \
               (i['new'] == 'Y') == args['new'] and \
               i['region'] == ses.region_name:
                break
        else:
            lg.error('AMI not found')
            return

        lg.info('AMI: {}'.format(i['ami']))

        number=args.get('number', 1)
        try:
            for cnt in range(1): # args['number']):
                Instances = ses.resource('ec2').create_instances(
                    ImageId=i['ami'],
                    InstanceType='t2.'+args['type'],
                    MinCount=number, MaxCount=number,
                    KeyName=Key_Name,
                )
                # Store OS because init_instance will behave differently
                created=tuple({'instance_id':_.id} for _ in Instances)
                self.instances.extend(created)
        except:
            lg.exception("Create multi Instances Error")
            return

        return created

    def terminate_instances(self, profile, instances=[]):
        """
        * instances is an empty list: Terminate all instances with the ids stored in instances.csv 
        * instances is a tuple of instance_ids: terminate these instance_ids
        :return:
        """
        ses=self.get_session(profile)

        if not instances: instances=[_['instance_id'] for _ in self.instances]
            
        for item in instances:
            instance_item = ses.resource('ec2').Instance(item)
            response = instance_item.terminate()
            lg.info('terminate response: {}'.format(response))
        # TODO: check for errors
        self.instances=[_ for _ in self.instances # Remove only deleted ones
                        if _['instance_id'] not in instances]

def start():
    """
    Entry point function
    :return: 
    """
    # Input Argument ("source image path and output path")
    ap = ArgumentParser(description='Create EC2 instance with Linux or Windows from the AMI. Please look at the amilist.csv for the mapping.')
    ap.add_argument('-t', dest='type', help='Instance type',
                    choices=('nano', 'micro', 'small', 'medium', 'large',
                             'xlarge', '2xlarge'), default='medium')

    # HVM virt for t2.medium is required
    ap.add_argument("-o", dest="ostype", help="OS type to create: LA - linux arch, LU - linux ubuntu, W - windows",
                    choices=('LA', 'LU', 'W'))
    ap.add_argument("-n", dest='new', help="Brand-new instance or preset",
                    action="store_true", default=True)
    ap.add_argument("-N", "--number", help="The number of instances you want to make", type=int, default=1)
    ap.add_argument("-c", "--credentials",
                    help="get instance parameters for connection",
                    action="store_true")
    ap.add_argument("-T", "--terminate", help="terminate instances.",
                    action="store_true")
    ap.add_argument('profile',
                    help="Profile to use for AWS (section in AWS credentials")
    ap.add_argument('instance', help="Instance id(s) to work with. Currently only mass-destruction is supported",
                    nargs='*')
    args = vars(ap.parse_args())
    lg.debug('args: {}'.format(args))

    manager = instance_manager()

    if args["credentials"]:
        manager.decrypt_ec2_secure_info(args['profile'])
    elif args["terminate"]:
        manager.terminate_instances(args['profile'], args['instance'])
    else:
        manager.create_key(args['profile'])
        res=manager.create_multi_instances(args['profile'], args)
        if res:
            lg.info('Created: {}'.format(res))
        else:
            lg.warning('create_instance has failed')

if __name__ == '__main__':
    try:
        start()
    except (SystemExit, KeyboardInterrupt):
        pass
    except:
        lg.exception('main routine')
