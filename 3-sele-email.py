import requests
from bs4 import BeautifulSoup
import os
import webbrowser
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from subprocess import Popen, PIPE
import datetime as dt
import logging
import getpass
import yaml

# setting up logger
logger = logging.getLogger(__name__)
logging.basicConfig(filename='/tmp/amfam_log.txt',level=logging.DEBUG, format='%(asctime)s-%(levelname)s-%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logging.debug('Starting logging.')

def load_yaml_config(yaml_file):
    with open(yaml_file,'r') as stream:
        try:
            yaml_data=yaml.load(stream)
        except yaml.YAMLError as exc:
            logging.debug('YAML error:'+exc)
    return yaml_data

def get_today_date():
    now = dt.datetime.now()
    return now.strftime("%Y-%m-%d")

def run_script(script, *args):
    p = Popen(['osascript', '-'] + [arg for arg in args], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    stdout, stderr = p.communicate(script)
    print (p.returncode, "\nstdout is", stdout, "errcode is", stderr)
    return stdout

SELECT_CLASSES_DROPDOWN = (By.ID,'selectClasses')

# setting chrome driver options
mobile_emulation = {
    "deviceMetrics": { "width": 360, "height": 640, "pixelRatio": 3.0 },
    "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19" }
options = Options()
options.headless = True
options.add_experimental_option("mobileEmulation", mobile_emulation)


url='https://amfamfit.com/richmond-short-pump/group-fitness/class-schedules/'
# headers = {'User-agent':'Mozilla/5.0 (Linux; Android 7.0; SM-G930V Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Mobile Safari/537.36'}
# r = requests.get(url, headers=headers)
# r = requests.get(url)

# check if file with today's schedule already exists
today_date=get_today_date()

# building path to schedule file
username = getpass.getuser() # in case want to use it to define target directory
source_dir = '/.own_temp_files'
source_dir=os.path.expanduser("~")+source_dir # directory for log files
sched_file=source_dir+'/amfam_sched-'+today_date+'.txt'

if not os.path.isfile(sched_file):
    logging.debug('File now found. Launching Selenium try block.')

    try:
        driver = webdriver.Chrome(chrome_options = options)
        driver.get(url)
        class_dropdown = WebDriverWait(driver,300).until(EC.presence_of_element_located(SELECT_CLASSES_DROPDOWN))
        html = driver.page_source
        with open(sched_file,'w') as f:
            f.write(html)
    except(NoSuchElementException,TimeoutException) as e:
        # fail the Test if the element can not be found or timeout occurs
        print('Test failed, the class drop down could not be found ')
    finally:
        driver.quit()

else:
    # load html variable from sched_file
    with open(sched_file, 'r') as f:
        html=f.read()

soup=BeautifulSoup(html,'lxml')
r=soup.find_all('td',{"id":"tdClass","style":"padding:4px"})
schedule=""
classes_of_interest=['zumba','yoga','groove','barre',]
include_class=False
for c in r:
    time=c.find('div',{"class":"MVbigLabel","style":"padding:2px"})
    classname=c.find('div',{"class":"MVbigLabel","style":"padding:4px"})
    instructor=c.find('div',{"class":"MVmediumLabel"})
    for class_name in classes_of_interest:
        if class_name in classname.text.lower():
            include_class=True
            break
    if include_class:
        line=time.text+" "+classname.text+" "+instructor.text+"\n"
        print(line)
        schedule=schedule+line
    include_class=False
last_line='\nThe URL for full schedule is: %s' %(url)+'\n'
schedule=schedule+last_line

# getting ready to read config.yaml from current directory
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
yaml_data = load_yaml_config('amfam_config.yaml')

import smtplib
from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# msg = MIMEMultipart()
# msg['From'] = 'shoryamal@gmail.com'
# msg['To'] = 'smalani@fastmail.com'
# msg['Subject'] = 'amfamfit schedule for today'

# message = 'Subject: {}\n\n{}'.format('amfam schedule', schedule)

smtp_login = yaml_data['smtp_login']
smtp_pass = yaml_data['smtp_pass']
recipients = yaml_data['recipients']
sender = yaml_data['sender']

mail = smtplib.SMTP('smtp.gmail.com',587)
mail.ehlo()
mail.starttls()
mail.login(smtp_login,smtp_pass)

msg = MIMEText(schedule)
msg['Subject'] = "amfamfit for "+today_date
msg['From'] = sender
msg['To'] = ", ".join(recipients)

# mail.sendmail(sender,recipients,message.encode('utf-8'))
mail.sendmail(sender,recipients,msg.as_string())
mail.quit()