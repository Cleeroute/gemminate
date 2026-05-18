import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Chrome(options=options)
driver.get("http://localhost:8000/")

# Try signup
driver.execute_script("""
    // Switch to signup
    document.querySelectorAll('.text-blue-600')[0].click();
""")
time.sleep(1)

driver.execute_script("""
    document.querySelector('input[type="email"]').value = 'test999@example.com';
    document.querySelector('input[type="password"]').value = 'password';
    document.querySelector('button[type="submit"]').click();
""")

time.sleep(3)
driver.get("http://localhost:8000/dashboard")
time.sleep(3)

driver.save_screenshot("screenshot.png")
print("Saved screenshot.png")

for entry in driver.get_log('browser'):
    print(entry)

driver.quit()
