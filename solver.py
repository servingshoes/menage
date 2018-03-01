#!/usr/bin/env python
#aikipooh@gmail.com

from os import getcwd, path

from time import sleep, time
from datetime import time as dt_time, date, datetime, timedelta, timezone
from logging import basicConfig, DEBUG, INFO, WARNING, ERROR, StreamHandler,\
    getLogger
from contextlib import suppress
from csv import DictReader
from pdb import set_trace
#from json import dump
from threading import Thread #, Lock, Event

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, \
    ElementNotInteractableException, NoSuchWindowException, \
    NoSuchElementException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import Firefox, FirefoxProfile, PhantomJS
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

num_threads=10

solve_url="http://www.supremenewyork.com:5000/solve"
solve_url="http://kith.com:5000/solve"

# Need to sleep until the moment X (11:00:05 or 16:00:05 UTC) where we start
#drophour=11
drophour=16

headless = False #True

debug=1

class Filter:
    def filter(event):
        return event.name not in ('requests.packages.urllib3.connectionpool',
                                  'selenium.webdriver.remote.remote_connection')

h=StreamHandler()
h.addFilter(Filter)

ll=WARNING
#ll=INFO
ll=DEBUG

basicConfig(format='{asctime} {threadName:11s}: {message}', datefmt="%H:%M:%S",
            style='{', level=ll, handlers=[h])

lg=getLogger(__name__)

accounts=[]
with open('100 Gmail.csv') as f:
    rd=DictReader(f)
    for i in rd:
        i['name']=i['Email'].split('@')[0]        
        accounts.append(i)

#If running headless, create new virtual display
if headless:
    from pyvirtualdisplay import Display
    from sys import stderr
    from os import devnull, dup, dup2

    saved = dup(stderr.fileno())
    with open(devnull, 'w') as null:
        dup2(null.fileno(), stderr.fileno())            

        display = Display(visible=0, size=(1366, 768))
        display.start()
        
    dup2(saved, stderr.fileno()) # Restore back

class gmail(Thread):
    def __init__(self, account):
        name=account['name']
        
        super().__init__(name=name) # Thread __init__
        
        lg.warning('{0[name]}, proxy: {0[Proxy]}'.format(account))

        self.account=account
        self.solved=0
        
        if 0: # Getting cookies snippet
            print(self.driver.get_cookies())
            cookies={_['name']:_['value'] for _ in self.driver.get_cookies()}
            with open('cookies.json', 'w') as f: dump(cookies, f, indent=4)

    def verify(self, el):
        '''Verifies the account. May be untrivial:('''
        
        text=el.text # get_attribute('value')
        lg.info('Text: {}'.format(text))
        if text == "Verify it's you":
            lg.debug('Verify')
            #el=self.driver.find_element_by_id('identifierNext')
            el=self.driver.find_element_by_xpath(
                '//div[.="Confirm your recovery email"]')
            print(el)
            el.click()            
            el=WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located((By.NAME, 'knowledgePreregisteredEmailResponse'))
            )
            el.send_keys(account[2]) # recovery email

    def login(self):
        if 0: # to test
            #'https://www.whoishostingthis.com/tools/user-agent/'
            self.driver.get('about:about')
            sleep(1000)
        #self.driver.get('https://mail.google.com')
        self.driver.get('https://accounts.google.com/signin/v2/identifier?continue=https%3A%2F%2Fmail.google.com%2Fmail%2F&service=mail&sacu=1&rip=1&flowName=GlifWebSignIn&flowEntry=ServiceLogin')
        prefilled=False

        lg.debug('Logging in with {}'.format(self.account))
        try:
            el=WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.ID, 'identifierId'))
            )
        except TimeoutException:
            prefilled=True

        if prefilled:
            lg.info('Username prefilled already')
        else:
            lg.debug('Entering username')
            el.send_keys(self.account['name']) # username
            nxt=self.driver.find_element_by_id('identifierNext')
            nxt.click()

        logged_in=False
        try:
            el=WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.NAME, 'password'))
            )
        except TimeoutException: # We're logged in?
            # TODO: Check for something visible after being logged in
            # Because we may genuinely be in timeout
            logged_in=True

        if logged_in:
            lg.info('Logged in already')
        else:
            lg.debug('Entering password')
            el.send_keys(self.account['Second Password'])
            nxt=WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, 'passwordNext'))
            )
            nxt.click()

            # WebDriverWait(self.driver, 60).until(
            #     EC.frame_to_be_available_and_switch_to_it((By.ID, 'tab1_1'))
            # )

            try:
                el=WebDriverWait(self.driver, 3).until(
                    EC.visibility_of_element_located((By.ID, 'headingText'))
                )
                #open('1.html','w').write(self.driver.page_source)
                self.verify(el)
            except TimeoutException: # We're in
                pass

    def screenshot(self, name):
        self.driver.save_screenshot(
            '{}/{}-{}.png'.format(getcwd(), self.account['name'], name))
        
    def solve(self):
        '''Solve the captcha one time'''
        WebDriverWait(self.driver, 30).until(
            EC.frame_to_be_available_and_switch_to_it(
                (By.XPATH, '//iframe[@title="recaptcha widget"]'))
        )

        el=WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div.recaptcha-checkbox-checkmark'))
        )
        #lg.info(el
        el.click()

        lg.debug('Clicked solve box')

        def check_style(driver, el):
            '''Now need to see what happened there. Check an attribute to see if we're successful.'''
            attr=el.get_attribute('aria-checked')
            lg.debug(attr)
            return attr == 'true'

        lg.debug('Before check_style')
        timeout=False
        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: check_style(
                    driver, self.driver.find_element_by_id('recaptcha-anchor'))
            )
        except TimeoutException:
            timeout=True # Next (very soon) we'll see what happened 

        lg.debug('Final: '+self.driver.find_element_by_id('recaptcha-anchor').get_attribute('aria-checked'))

        self.driver.switch_to.default_content()
        if timeout:
            lg.warning('Timeout')
            self.screenshot('timeout')
            el=self.driver.find_element_by_xpath('//iframe[@title="recaptcha challenge"]')
            #set_trace()
            self.driver.switch_to.frame(el)
            l=len(self.driver.page_source)
            lg.debug(l)
            with open('recaptcha_main.html', 'w') as f: f.write(self.driver.page_source)
            if l > 10000:
                lg.warning('Captcha')
                self.screenshot('captcha')
                return True # Need to quit
            self.driver.switch_to.default_content()
            self.driver.refresh()
        else:
            el=self.driver.find_element_by_id('submit')
            el.click() # Submit button
            lg.info('Clicked submit')

            lg.debug('Before staleness')
            WebDriverWait(self.driver, 10, poll_frequency=0.1).until(
                EC.staleness_of(el)
            )
            lg.debug('After staleness')

    def create_driver(self):
        if 1:
            caps = DesiredCapabilities().FIREFOX.copy()

            profile_path=path.expanduser('~')+'/.mozilla/firefox/'+self.account['name']

            # caps['proxy'] = {
            caps['moz:firefoxOptions'] = {
                "args": ["-profile", profile_path], # geckodriver 0.18+
            }

            profile=FirefoxProfile(profile_path)
            #profile.set_preference("general.useragent.override", 'Mozilla/5.0 (X11; Linux x86_64; rv:56.0) Gecko/20100101 Firefox/56.0')

            self.driver = Firefox(profile, capabilities=caps)
            #self.driver = Firefox(profile)
        else: # PhantomJS
            # https://github.com/detro/ghostdriver
            caps = DesiredCapabilities().PHANTOMJS
            caps["phantomjs.page.settings.userAgent"] = \
                'Mozilla/5.0 (X11; Linux x86_64; rv:56.0) Gecko/20100101 Firefox/56.0'
            service_args = [
                '--proxy={}'.format(':'.join(self.account['Proxy'].split(':')[:2])),
                '--proxy-type=http',
            ]
            print(service_args)
            self.driver = PhantomJS(service_args=service_args, capabilities=caps)
            self.driver.set_window_size(1120, 550)
                    #profile.set_preference("general.useragent.override","Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16")
        #profile.set_preference("general.useragent.override","Mozilla/5.0 (X11; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0")
        # profile.set_preference("browser.startup.homepage_override.mstone", "ignore");
        # profile.set_preference("startup.homepage_welcome_url.additional",  "about:blank");
        # profile.set_preference("xpinstall.signatures.required", "false");
        # profile.set_preference("toolkit.telemetry.reportingpolicy.firstRun", "false");


    def run(self):
        '''Login and run in cycle'''

        self.create_driver()
        
        try:
            self.login()
        
            tosleep=datetime.combine(
                date.today(), dt_time(drophour,00,5,tzinfo=timezone.utc))-\
                datetime.now(timezone.utc)
            tosleep=tosleep.seconds
            lg.info('Sleeping for {}'.format(tosleep))
            if '/pooh/' in path.expanduser('~'): tosleep=0 # don't sleep on developer's host
            if not debug: sleep(tosleep)

            # Creating new window to work in (otherwise sometimes the page will ask whether we're ok to leave it)
            self.driver.execute_script('''window.open('{}',"_blank");'''.format(solve_url))
            self.driver.switch_to.window(self.driver.window_handles[-1])
            lg.debug('Created new window')
        
            # Cycle here getting tokens until there are no more nocaptcha
            start_time=end_time=time() # In case we have exception
            while True:
            #for i in range(1):
                if self.solve(): break
                self.solved+=1
            end_time=time()
        except:
            lg.exception('In run')
            self.screenshot('exception')
        finally:            
            lg.warning('Closing driver')
            with suppress(WebDriverException): self.driver.quit()
        rate=(end_time-start_time)/self.solved if self.solved else 0
        lg.warning('Solved: {} ({:.2f})'.format(self.solved, rate))
            
workers=[]
num=0
if debug:
    num=0
    num_threads=1
for acc in accounts[num:num+num_threads]: # Let's start all workers first
    worker=gmail(acc)
    #workers.append((acc[0], worker))
    workers.append(worker)
    worker.start()

for t in workers:
    t.join()
lg.debug('Finished')

# try:
#     v.login()
# finally:
#     print('closing')
#     v.driver.close()
