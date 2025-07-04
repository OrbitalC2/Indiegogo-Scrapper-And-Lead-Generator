import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse

class Client:
    def __init__(self):
        self.session = requests.Session()
        self.baseURL = "https://www.indiegogo.com"
        self.csrf = None
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })

    def initSesssion(self):
        print("Initializing Session\n")

        response = self.session.get(self.baseURL)

        print(f"Initial Cookies: {len(self.session.cookies)}")

        self.csrf = self.extractCSRF(response.text)

        if self.csrf:
            print(f"CSRF Token Extracted: {self.csrf}")
            self.session.headers['X-CSRF-Token'] = self.csrf
        else:
            print("No CSRF token found")
        
        return True

    def extractCSRF(self, htmlContent):
        soup = BeautifulSoup(htmlContent, 'html.parser')

        #look in the meta tag to find csrf token (basic)
        csrfToken = soup.find('meta', {'name': 'csrf-token'})
        if csrfToken:
            return csrfToken.get('content')
        
          # Haalat kharab houn to script tags mein dhoondein
        # script_tags = soup.find_all('script')
        # for script in script_tags:
        #     if script.string:
        #         # Look for various CSRF token patterns
        #         patterns = [
        #             r'csrf[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        #             r'_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        #             r'authenticity[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)["\']'
        #         ]
                
        #         for pattern in patterns:
        #             match = re.search(pattern, script.string, re.IGNORECASE)
        #             if match:
        #                 return match.group(1)
        
         # Allahuakbar
        # csrf_input = soup.find('input', {'name': re.compile(r'csrf|_token', re.IGNORECASE)})
        # if csrf_input:
        #     return csrf_input.get('value')
        
        return None
    
    def getCompleteCookieData(self):
        print("Visiting explore -page to get additional cookies")
        explorePageURL = f"{self.baseURL}/explore/all?project_timing=all&product_stage=all&ended_campaigns_included=false&sort=trending"

        self.session.headers['Referer'] = self.baseURL

        response = self.session.get(explorePageURL)
        response.raise_for_status()

        print(f"Explore page visited. Total cookies: {len(self.session.cookies)}")
        return response
    
    def getProjectData(self, projectSlug):
        #visit project page
        projectURL = f"{self.baseURL}/projects/{projectSlug}"

        #will also need to change referer
        self.session.headers['Referer'] = f"{self.baseURL}/explore/all?project_timing=all&product_stage=all&ended_campaigns_included=false&sort=trending"

        print(f"Fetching Project {projectURL}")
        
        response = self.session.get(projectURL)
        response.raise_for_status()

        return response
    
    def extractOwnerInfo(self, htmlContent):
            try:
                soup = BeautifulSoup(htmlContent, 'html.parser')
                scriptTags = soup.find_all('script')

                for script in scriptTags:
                    if script.string and 'gon.trust_passport' in script.string:
                        scriptContent = script.string

                        passportMatch = re.search(r'gon\.trust_passport\s*=\s*(\{.*?\});', scriptContent, re.DOTALL)
                        if passportMatch:
                                passportJSONstr = passportMatch.group(1)

                                try:
                                    passportData = json.loads(passportJSONstr)
                                    ownerData = passportData.get('owner', {})

                                    return{
                                        'name': ownerData.get('name'),
                                        'linkedin_profile_url': ownerData.get('linkedin_profile_url'),
                                        'twitter_profile_url': ownerData.get('twitter_profile_url'),
                                        'website_url': ownerData.get('website_url', 'N/A') if ownerData else 'N/A'
                                    }
                                except json.JSONDecodeError as e:
                                        print(f"Error parsing gon.trust.passport JSON: {e}")

            except Exception as e:
                print(f"Error in extract_owner_info: {e}")
                return None
            
    
    def extractFullObject(self, htmlContent):
        try:
            soup = BeautifulSoup(htmlContent, 'html.parser')
            scriptTags = soup.find_all('script')

            for script in scriptTags:
                if script.string and 'gon.trust_passport' in script.string:
                    scriptContent = script.string

                    passportMatch = re.search(r'gon\.trust_passport\s*=\s*(\{.*?\});', scriptContent, re.DOTALL)

                    if passportMatch:
                        passportJSONstr = passportMatch.group(1)
                        try:
                            return json.loads(passportJSONstr)
                        except:
                            print(f"Error parsing full trust passport: {e}")
                            return None
            return None
        
        except Exception as e:
            print(f"Error in extractFullObject: {e}")
            return None
        
    def get_cookies_dict(self):
        return {cookie.name: cookie.value for cookie in self.session.cookies}
    
    def get_headers_dict(self):
        return dict(self.session.headers)
    

    def extractKeywords(self, htmlContent):
        try:
            soup = BeautifulSoup(htmlContent, 'html.parser')

            keywords = soup.find('meta', {'name' : 'keywords'})
            if keywords:
                return keywords.get("content")
            else:
                print("Keywords not present\n")
                return None
            
        except Exception as e:
            print(f'Error extracting keywords {e}')

                         
                        

def main(project_slug):
    client = Client()
    client.initSesssion()
    client.getCompleteCookieData() #visits explore page

    projectSlug = "merinotech-2-0-no-odor-outdoor-gear-innovation"
    response = client.getProjectData(project_slug)

    print(f"Response status: {response.status_code}")
    print(f"Response size: {len(response.text)} characters")

    ownerInfo = client.extractOwnerInfo(response.text)
    fullInfo = client.extractFullObject(response.text)
    keywords = client.extractKeywords(response.text)

    if keywords:
        print(f'Keywords: {keywords}')

    if ownerInfo:
        print("OWNER: ")

        name = ownerInfo.get('name', 'Not found')
        linkedinURL = ownerInfo.get('linkedin_profile_url', 'Not found')
        twitterURL = ownerInfo.get('twitter_profile_url', 'Not found')
        website = ownerInfo.get('website_url')

        print(f"Name: {name}")
        print(f"Linkedin URL: {linkedinURL}")
        print(f"Twitter URL: {twitterURL}")
        print(f"Website URL: {website}")

        print("\n--- Full Owner Data (for debugging) ---")
        print(json.dumps(fullInfo, indent=2))
    # else:
    #     print("\nNo owner information found. Trying to extract full trust passport")
    #     fullPassport = client.extract_full_trust_passport(response.text)

    #     if fullPassport:
    #         print("Full trust passport found:")
    #         print(json.dumps(fullPassport, indent=2))

    
    soup = BeautifulSoup(response.content, 'html.parser')
    pretty = soup.prettify()  

    with open('project_page_pretty.html', 'w', encoding='utf-8') as f:
        f.write(pretty)

    print("Pretty-printed HTML saved to project_page_pretty.html")


slug = "volla-tablet-simplify-your-digital-life"
main(slug)