
import json, re, time, random, signal, sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


inputJSON   = "leads_clone.json"
outputJSON  = "after99(incl).json"
chromeDriver = "/home/rayyan/.wdm/drivers/chromedriver/linux64/138.0.7204.49/chromedriver-linux64/chromedriver"
startingLead     = 99
maxLeads    = 29
maxCaptchaRetries = 3         
emailRegex = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
partURL   = "https://www.partURL.com/search?q="

#optional extra to avoid bot detection,
userStrings = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.6261.70 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def chrome_driver():
    opt = webdriver.ChromeOptions()
    # opt.add_argument("--headless=new") keeping visible to avoid bot detection
    opt.add_argument("--disable-blink-features=AutomationControlled")
    opt.add_argument(f"--user-agent={random.choice(userStrings)}")
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    opt.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(service=Service(chromeDriver), options=opt)


def search_emails(driver, query, delay):
    driver.get(partURL + query.replace(" ", "+"))
    time.sleep(delay)

    #simulate human behaviour by scrolling
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2)")
    time.sleep(1.5)

    try:                                      
        driver.find_element(By.XPATH, "//button[contains(text(),'Accept')]").click()
    except Exception:
        pass

    if "sorry/index" in driver.current_url or "captcha" in driver.page_source.lower():
        raise RuntimeError("Captcha page")

    snippets = driver.find_elements(By.CSS_SELECTOR, "div.VwiC3b")
    return list({m.group(0) for sn in snippets for m in emailRegex.finditer(sn.text)})


def write_progress(path: str, data):
    Path(path).write_text(json.dumps(data, indent=2))
    print(f"\nProgress saved to {path}")


def main():
    leads = json.loads(Path(inputJSON).read_text())
    driver = chrome_driver()
    done = 0
    
    #check ctrl-c interrupt
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    try:
        for idx, lead in enumerate(leads[startingLead:], startingLead):
            if maxLeads and done >= maxLeads:
                break
            if lead.get("email_status") == "verified":
                continue

            founder = (lead.get("founder_name") or "").strip()
            if not founder:
                continue

            query = f'"{founder}" email OR contact'
            print(f"[{idx}] {founder} → searching…")

            captcha_tries = 0
            while True:
                try:
                    hits = search_emails(driver, query, random.randint(3, 8))
                    lead["emails"] = hits
                    lead["email"] = hits[0] if hits else None
                    lead["email_status"]  = "found-unverified" if hits else "not-found"
                    print("   ", "✅" if hits else "❌", hits)
                    break                                  
                except RuntimeError:
                    #CAPTCHA
                    captcha_tries += 1
                    if captcha_tries > maxCaptchaRetries:
                        lead["email"]        = None
                        lead["emails"]       = []
                        lead["email_status"] = "captcha-skipped"
                        print("   ⛔ CAPTCHA x3 – skipping lead")
                        break
                    print(f"   CAPTCHA – restart #{captcha_tries}")
                    driver.quit()
                    time.sleep(random.randint(8, 15))
                    driver = chrome_driver()                # new session

            done += 1
            if done % 12 == 0:
                #after every 12 leads, simulate a 'coffee break'
                pause = random.randint(20, 40)
                print(f"   cooling {pause} s…")
                time.sleep(pause)

    except KeyboardInterrupt:
        print("\n⛔  Interrupted by user.")

    finally:
        driver.quit()
        write_progress(outputJSON, leads)
        print(f"Processed {done} leads. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
