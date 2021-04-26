
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located, element_to_be_clickable
from selenium.webdriver.common.action_chains import ActionChains
import time
import random 
'''
    Script to generate Samsung Smartthings simulation test data, using Selenium
    This is used to generate our DataEnvironmentSamsung.txt
'''

browser = webdriver.Firefox()
browser.get("https://graph.api.smartthings.com/")

#first need to log in
browser.find_element_by_xpath("//a[@href='/login/auth']").click()
time.sleep(1)
browser.find_element_by_name("saLoginFrm").click()
time.sleep(1)

username = browser.find_element_by_id("iptLgnPlnID")
username.clear()
username.send_keys("yifeiy3@andrew.cmu.edu")
password = browser.find_element_by_id("iptLgnPlnPD")
password.clear()
password.send_keys("zz081620")

browser.find_element_by_id("signInButton").click()

#there is a pop up page about secure login, delete this part when pop up page not there anymore
WebDriverWait(browser, 5).until(presence_of_element_located((By.ID, "btnNotNow"))).click()

#should be logged in now
time.sleep(1)
mySmartApp = browser.find_elements_by_xpath("//ul[@class='nav navbar-nav main']//li[@class='']")
mySmartApp[3].click() #this should be of My SmartApps button

#Open "Household device" app
WebDriverWait(browser, 5).until(presence_of_element_located(
    (By.XPATH, "//a[@href='/ide/app/editor/ef6b1a8c-b2f6-457c-865a-643242f99b8b']"))).click()

#Now we need to install the app
WebDriverWait(browser, 10).until(presence_of_element_located(
    (By.XPATH, "//button[@class='btn btn-default btn-sm run-btn']"))).click()
WebDriverWait(browser, 5).until(presence_of_element_located(
    (By.XPATH, "//button[@class='btn btn-small btn-success set']"))).click()
time.sleep(3)
prefoptions = browser.find_elements_by_xpath(
    "//div[@class='content accordion-inner preferences-wrap']//div[@class='section']")
for dropdowns in prefoptions:
    dropdowns.click()
    time.sleep(2)

#install the 4 devices
browser.find_element_by_xpath(
    "//input[@id='switch1' and @value='4db1d2f7-41d5-466a-8d48-570f14ca4886']"
).click()
browser.find_element_by_xpath(
    "//input[@id='switch2' and @value='abeafef6-7372-4347-bab6-4f485b8fb2d7']"
).click()
try:
    browser.find_element_by_xpath(
        "//input[@id='smokeAlarm' and @value='25afa2d1-8013-454d-bd42-7b5a9fa87173']"
    ).click()
except:
    prefoptions[2].click()
    browser.find_element_by_xpath(
        "//input[@id='smokeAlarm' and @value='25afa2d1-8013-454d-bd42-7b5a9fa87173']"
    ).click()

browser.find_element_by_xpath(
    "//input[@id='door' and @value='c4a159b1-cadd-41aa-9b17-cc0e9643c9a8']"
).click()
browser.find_element_by_id("update").click()

#get device buttons
vs1 = WebDriverWait(browser, 10).until(presence_of_element_located((By.XPATH,
    "//div[@class='tile tile-standard wmain hmain device' and \
    @data-device='4db1d2f7-41d5-466a-8d48-570f14ca4886']"
)))                                     #virtual switch 1
vs2 = WebDriverWait(browser, 10).until(presence_of_element_located((By.XPATH,
    "//div[@class='tile tile-standard wmain hmain device' and \
    @data-device='abeafef6-7372-4347-bab6-4f485b8fb2d7']"
)))                                        #virtual switch 2
door =   WebDriverWait(browser, 10).until(presence_of_element_located((By.XPATH,
    "//div[@class='tile tile-standard wmain hmain device' and \
    @data-attr='lock' and @data-device='c4a159b1-cadd-41aa-9b17-cc0e9643c9a8']"
)))                                         #door 

#start generating data  
for i in range(1500):
    rv1 = random.random()
    if rv1 > 0.7:
        vs1.click()
        print('Light A is clicked')
    elif rv1 < 0.5:
        vs2.click()
        print('Light B is clicked')
    else:
        door.click()
        print('Door is clicked')
    time.sleep(3)