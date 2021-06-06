
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located, element_to_be_clickable
from selenium.webdriver.common.action_chains import ActionChains
import time
import random 
'''
    Example Script to generate Samsung Smartthings simulation test data, using Selenium
    This is used to generate our DataEnvironmentSamsung2.txt
'''

browser = webdriver.Firefox() #Any supported brower type
browser.get("https://graph.api.smartthings.com/") #Samsung hub link

#first need to log in
browser.find_element_by_xpath("//a[@href='/login/auth']").click()
time.sleep(1)
browser.find_element_by_name("saLoginFrm").click()
time.sleep(1)

username = browser.find_element_by_id("iptLgnPlnID")
username.clear()
username.send_keys("your_account_username")
password = browser.find_element_by_id("iptLgnPlnPD")
password.clear()
password.send_keys("your_account_password")

browser.find_element_by_id("signInButton").click()

#there is a pop up page about secure login, delete this part when pop up page not there anymore
WebDriverWait(browser, 5).until(presence_of_element_located((By.ID, "btnNotNow"))).click()

#should be logged in now, wait 2 seconds for page to load
time.sleep(2)
mySmartApp = browser.find_elements_by_xpath("//ul[@class='nav navbar-nav main']//li[@class='']")
mySmartApp[3].click() #this should be of My SmartApps button


#Open app, wait 5 seconds max since sometimes browser need time to load
#4d25e960-105e-40d1-ba56-2a33ec53480f can be replaced by your app's id.
WebDriverWait(browser, 5).until(presence_of_element_located(
    (By.XPATH, "//a[@href='/ide/app/editor/4d25e960-105e-40d1-ba56-2a33ec53480f']"))).click()

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

#install devices for the app
#The input id is the name you give to your devices in preference section, value is your desired device's id.
browser.find_element_by_xpath(
    "//input[@id='switches' and @value='4db1d2f7-41d5-466a-8d48-570f14ca4886']"
).click()

#get button to simulate app touch.
trigger = WebDriverWait(browser, 10).until(presence_of_element_located((By.XPATH,
    "//div[@class='toolbar']//button[@class='btn btn-xs btn-default simulate-touch']"    
)))

#start the app simulation
browser.find_element_by_id("update").click()

#get device buttons, data-device is the id for device
device1 = WebDriverWait(browser, 10).until(presence_of_element_located((By.XPATH,
    "//div[@class='tile tile-standard wmain hmain device' and \
    @data-device='4db1d2f7-41d5-466a-8d48-570f14ca4886']"
)))   

#Example generation of data:
for i in range(800):
    rv1 = random.random()
    if rv1 > 0.7:
        device1.click()
        print("device1 is clicked")
    elif rv1 < 0.3:
        trigger.click()
        print("app is touched")
    time.sleep(1)