#!/usr/bin/env python

from logging import getLogger, basicConfig, DEBUG, INFO, WARNING, ERROR

from flask import Flask, render_template, request
from boto3 import session
#from OpenSSL import SSL

app = Flask(__name__)

getLogger('boto3').setLevel(WARNING) # If it'll try to print that giant output json, the hell would freeze over before it finishes
getLogger('botocore').setLevel(INFO)
getLogger('werkzeug').setLevel(ERROR)

lg=getLogger(__name__)

ll=WARNING
ll=INFO
ll=DEBUG

from socket import gethostname
if gethostname() == 'pooh':
    basicConfig(format='{asctime}: {message}', datefmt="%H:%M:%S", style='{',
                level=ll)
else:
    basicConfig(format='{asctime}: {message}', datefmt="%H:%M:%S", style='{',
                filename='obtain.log', #.format(time()),
                level=ll)

params={
    'supreme': { # Supremenewyork.com
        'sitekey': '6LeWwRkUAAAAAOBsau7KpuC9AV-6J8mhw4AjC3Xz',
        'queue': 'notime.fifo',
        'msg_group_id': 'Fastcaptcha1'
    },
    'kith': { # kith.com - Monday at 16:00 GMT
        'sitekey': '6LeoeSkTAAAAAA9rkZs5oS82l69OEYjKRZAiKdaF',
        'queue': 'HenryShopify',
        'msg_group_id': None
    },
    'google': { # Testing with google.com
        'sitekey': '6LfP0CITAAAAAHq9FOgCo7v_fb0-pmmH9VW3ziFs',
    }
}

profile='supreme'
profile='kith'

param=params[profile]
# Wordpress register
# sitekey='6LehfRgUAAAAAJbxrvWRaQ_uFq2ZO7jRM3VLcbFr'
# url="http://login.wordpress.org:5000/solve"

# http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/MakingRequests_MakingQueryRequestsArticle.html
session=session.Session(profile_name=profile)
lg.debug('session: {}'.format(session))
sqs = session.resource('sqs')
lg.debug('sqs: {}'.format(sqs))
queue = sqs.get_queue_by_name(QueueName=param['queue'])
lg.debug('queue: {}'.format(queue))

args={} # Create base args
if param['msg_group_id']: args['MessageGroupId']=param['msg_group_id']

# https://www.google.com/recaptcha/api/siteverify?secret=6Ld9mRUUAAAAALHyNPhGzo2cnvT86Z59WlyEoLWY&remoteip=85.201.212.72&response=
@app.route('/', methods=['GET', 'POST'])
@app.route('/solve', methods=['GET', 'POST'])
def solve():
    lg.debug(request.method)
    if request.method == "POST":
        lg.debug(request.form)
        token = request.form.get('g-recaptcha-response', '')
        lg.info("Token: {}".format(token))
        if token:
            args['MessageBody']=token
            response=queue.send_message(**args)
            lg.info(response['ResponseMetadata'])

    return render_template('index.html', sitekey=param['sitekey'])

#context = SSL.Context(SSL.SSLv23_METHOD)
# context.use_privatekey_file('yourserver.key')
# context.use_certificate_file('yourserver.crt')

lg.info('Starting')
#app.run(ssl_context='adhoc')
app.run()
