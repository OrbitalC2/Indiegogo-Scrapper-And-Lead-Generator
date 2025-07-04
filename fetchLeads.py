import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
# import gspread
# from google.oauth2.service_account import Credentials

class IndiegogoClient:
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

    def initSession(self):
        print("Initializing Session...")
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
        csrfToken = soup.find('meta', {'name': 'csrf-token'})
        if csrfToken:
            return csrfToken.get('content')
        return None
    
    def getCompleteCookieData(self):
        print("Visiting explore page to get additional cookies...")
        explorePageURL = f"{self.baseURL}/explore/all?project_timing=all&product_stage=all&ended_campaigns_included=false&sort=trending"
        self.session.headers['Referer'] = self.baseURL
        
        response = self.session.get(explorePageURL)
        response.raise_for_status()
        
        print(f"Explore page visited. Total cookies: {len(self.session.cookies)}")
        return response
    
    def getProjectData(self, projectSlug):
        projectURL = f"{self.baseURL}/projects/{projectSlug}"
        self.session.headers['Referer'] = f"{self.baseURL}/explore/all?project_timing=all&product_stage=all&ended_campaigns_included=false&sort=trending"
        
        print(f"Fetching Project: {projectURL}")
        response = self.session.get(projectURL)
        response.raise_for_status()
        return response
    
    def extractOwnerInfo(self, htmlContent):
      
        ownerData = {}
        location  = None

        try:
            soup = BeautifulSoup(htmlContent, 'html.parser')

            for script in soup.find_all('script'):
                text = script.string or ""

                #owner
                if 'gon.trust_passport' in text:
                    m = re.search(r'gon\.trust_passport\s*=\s*(\{.*?\});',
                                text, re.DOTALL)
                    if m:
                        try:
                            passport = json.loads(m.group(1))
                            ownerData = passport.get('owner', {})
                        except json.JSONDecodeError as e:
                            print("Error parsing trust_passport JSON:", e)

                #loc
                if 'gon.ga_impression_data' in text:
                    m = re.search(r'gon\.ga_impression_data\s*=\s*(\{.*?\});',
                                text, re.DOTALL)
                    if m:
                        try:
                            ga_data = json.loads(m.group(1))
                            location = ga_data.get('list')
                        except json.JSONDecodeError as e:
                            print("Error parsing ga_impression_data JSON:", e)

            # Nothing
            if not ownerData and location is None:
                return None

            return {
                'name': ownerData.get('name'),
                'linkedin_profile_url': ownerData.get('linkedin_profile_url'),
                'twitter_profile_url': ownerData.get('twitter_profile_url'),
                'location': location,
                'website_url': ownerData.get('website_url')
            }

        except Exception as e:
            print(f"Error in extractOwnerInfo: {e}")
            return None

    
    def extractKeywords(self, htmlContent):
        try:
            soup = BeautifulSoup(htmlContent, 'html.parser')
            keywords = soup.find('meta', {'name': 'keywords'})
            if keywords:
                return keywords.get("content")
            return None
        except Exception as e:
            print(f'Error extracting keywords: {e}')
            return None

class IndiegogoScraper:
    def __init__(self, target_keywords, google_sheets_creds=None):
        self.target_keywords = [keyword.lower().strip() for keyword in target_keywords]
        self.client = IndiegogoClient()
        self.google_sheets_creds = google_sheets_creds
        self.all_results = []
        
        self.api_data = {
            "variables": {
                "category_main": None,
                "category_top_level": "Tech & Innovation",
                "ended_campaigns_included": False,
                "feature_variant": "none",
                "page_num": 1,
                "per_page": 12,
                "product_stage": "all",
                "project_timing": "all",
                "project_type": "campaign",
                "q": None,
                "sort": "trending",
                "tags": []
            }
        }
        
        self.api_headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://www.indiegogo.com",
            "referer": "https://www.indiegogo.com/explore/tech-innovation?project_timing=all&product_stage=all&ended_campaigns_included=false&sort=trending",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "x-csrf-token": "juJKQhxIHmZB9K+S+doUq2+gGkXNngJE4o3mQ+vO+e1vf1kQIZMVFE7svz7bxo2T1hSbfEq4nPRIhkhcCsYO/w==",
            "cookie": "romref=dir-XXXX; romref_referer_host=; cohort=%7Cdir-XXXX; visitor_id=210b103356c499719b4e07d30f2a00f343c408bc4bfa48bb5ea4c732ebf7856e; analytics_session_id=238cb416fb63bce48e8cbd71e5ad77f296eb9aefcb9a0c4ea0d0e800f3c19d9b; accessibilityNoticeRenderedOnce=true; recent_project_ids=; _session_id=2d4cb9d50c67239e389dc34effefebad; x-spec-id=3fd2744ae9122d1021c7fa5120ab8023; _fbp=fb.1.1751310377196.234056032430069235; _ga=GA1.1.1299080479.1751310378; _gcl_au=1.1.1465586485.1751310378; _tt_enable_cookie=1; _ttp=01JZ13QAA8KVFV2HC3S5X4H84W*.tt.1; permutive-id=74299d73-25e5-41b3-9c07-9689b26c4c00; __ssid=567c02335be1ee71351d7ea34e6b13b; tcm={\"purposes\":{\"SaleOfInfo\":true,\"Analytics\":true,\"Functional\":true,\"Advertising\":true},\"timestamp\":\"2025-06-30T19:06:24.280Z\",\"confirmed\":true,\"prompted\":true,\"updated\":true}; __stripe_mid=460a7a9c-8a0a-4a8c-a243-9e16f90a67b56f5f75; __stripe_sid=f25de15d-c68c-4f6e-a6b7-e5817f04af48f304c8; newsletterDismissCount=1; newsletterLastDismiss=2025-06-30T19:06:33.619Z; ttcsid=1751310379340::gOBo5Bh4cel8GJOyLT2Q.1.1751311661789; _ga_DTZH7F2EYR=GS2.1.s1751310377$o1$g1$t1751311663$j57$l0$h1615441318; ttcsid_CC37ELBC77UFTO4NIRUG=1751310379340::gQ6TrU4ojJZSSbvs3Ddt.1.1751311694157"
        }
        
        self.api_url = "https://www.indiegogo.com/private_api/graph/query?operation_id=discoverables_query"

    def format_date(self, date_string):
        if not date_string:
            return "N/A"
        try:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")
        except:
            return date_string

    def clean_url(self, url):
        if url and url.startswith('/projects/'):
            return url[10:]  
        return url

    def extract_projects_from_response(self, result):
        projects = []
        data = result.get('data', {})
        
        if 'discoverables' in data and isinstance(data['discoverables'], list):
            projects = data['discoverables']
        else:
            for key, value in data.items():
                if isinstance(value, dict) and 'edges' in value:
                    projects.extend([edge.get('node', edge) for edge in value['edges']])
                elif isinstance(value, list):
                    projects.extend(value)
        
        return projects

    def check_keyword_match(self, keywords_string):
        if not keywords_string:
            return []
        
        keywords_list = [kw.lower().strip() for kw in keywords_string.split(',')]
        matched = []
        
        for target_keyword in self.target_keywords:
            for keyword in keywords_list:
                if target_keyword in keyword or keyword in target_keyword:
                    matched.append(target_keyword)
                    break
        
        return matched

    def scrape_projects(self, max_pages=None):
        print(f"Starting scrape with target keywords: {self.target_keywords}")
        
        # Initialize the client session
        self.client.initSession()
        self.client.getCompleteCookieData()
        
        page_num = 1
        
        while True:
            if max_pages and page_num > max_pages:
                print(f"Reached maximum pages limit: {max_pages}")
                break
                
            print(f"\n{'='*60}")
            print(f"PROCESSING PAGE {page_num}")
            print(f"{'='*60}")
            
            # Update pg num
            self.api_data["variables"]["page_num"] = page_num
            
            try:
                
                response = requests.post(self.api_url, json=self.api_data, headers=self.api_headers)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result is None:
                        print(f"Page {page_num} returned null. Stopping.")
                        break
                    
                    projects = self.extract_projects_from_response(result)
                    
                    if not projects:
                        print(f"Page {page_num}: No projects found. Stopping.")
                        break
                    
                    print(f"Found {len(projects)} projects on page {page_num}")
                    
                    # Process each project
                    for i, project in enumerate(projects, 1):
                        print(f"\nProcessing project {i}/{len(projects)}: {project.get('title', 'Unknown')}")
                        
                        project_url = self.clean_url(project.get('clickthrough_url', ''))
                        
                        if not project_url:
                            print("  - No URL found, skipping...")
                            continue
                        
                        try:
                            # Get project page for keywords
                            project_response = self.client.getProjectData(project_url)
                            keywords_string = self.client.extractKeywords(project_response.text)
                            
                            print(f"  - Keywords: {keywords_string}")
                            
                            # Check for keyword matches
                            matched_keywords = self.check_keyword_match(keywords_string)
                            
                            if matched_keywords:
                                print(f"MATCH FOUND! Keywords: {matched_keywords}")
                                
                                # Extract owner information
                                owner_info = self.client.extractOwnerInfo(project_response.text)
                                
                                # Compile all data
                                project_data = {
                                    'title': project.get('title', 'N/A'),
                                    'description': project.get('tagline', 'N/A'),
                                    'date_opened': self.format_date(project.get('open_date')),
                                    'project_url': project_url,
                                    'matched_keywords': ', '.join(matched_keywords),
                                    'founder_name': owner_info.get('name', 'N/A') if owner_info else 'N/A',
                                    'linkedin_url': owner_info.get('linkedin_profile_url', 'N/A') if owner_info else 'N/A',
                                    'twitter_url': owner_info.get('twitter_profile_url', 'N/A') if owner_info else 'N/A',
                                    'location': owner_info.get('location', 'N/A') if owner_info else 'N/A',
                                    'website_url': owner_info.get('website_url', 'N/A') if owner_info else 'N/A'
                                }
                                
                                self.all_results.append(project_data)
                                
                                print(f"  - Founder: {project_data['founder_name']}")
                                print(f"  - LinkedIn: {project_data['linkedin_url']}")
                                print(f"  - Twitter: {project_data['twitter_url']}")
                                print(f"  - Location: {project_data['location']}")
                                print(f"  - Company URL: {project_data['website_url']}")
                                
                            else:
                                print("NO MATCH, skipping...")
                            
                            # Add delay between requests
                            #time.sleep(1)
                            
                        except Exception as e:
                            print(f"  - Error processing project: {e}")
                            continue
                
                else:
                    print(f"Page {page_num}: API request failed with status {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"Page {page_num}: Request failed: {e}")
                break
            
            page_num += 1
            #time.sleep(0.5)  # Delay between pages
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE!")
        print(f"Total matched projects: {len(self.all_results)}")
        print(f"Pages processed: {page_num - 1}")
        print(f"{'='*60}")
        
        return self.all_results

    def save_to_json(self, filename='matched_projects.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {filename}")

    # def save_to_google_sheets(self, spreadsheet_name='Indiegogo Matched Projects'):
    #     if not self.google_sheets_creds:
    #         print("Google Sheets credentials not provided. Skipping Google Sheets upload.")
    #         return
        
    #     try:
    #         # Setup Google Sheets connection
    #         scope = ['https://www.googleapis.com/auth/spreadsheets', 
    #                 'https://www.googleapis.com/auth/drive']
            
    #         creds = Credentials.from_service_account_file(self.google_sheets_creds, scopes=scope)
    #         client = gspread.authorize(creds)
            
    #         # Create or open spreadsheet
    #         try:
    #             sheet = client.open(spreadsheet_name).sheet1
    #         except gspread.SpreadsheetNotFound:
    #             spreadsheet = client.create(spreadsheet_name)
    #             sheet = spreadsheet.sheet1
            
    #         # Clear existing data and set headers
    #         sheet.clear()
    #         headers = ['Founder Name', 'Title', 'Description', 'Date Opened', 
    #                   'LinkedIn URL', 'Twitter URL', 'Project URL', 'Matched Keywords']
    #         sheet.append_row(headers)
            
    #         # Add data rows
    #         for project in self.all_results:
    #             row = [
    #                 project['founder_name'],
    #                 project['title'],
    #                 project['description'],
    #                 project['date_opened'],
    #                 project['linkedin_url'],
    #                 project['twitter_url'],
    #                 project['project_url'],
    #                 project['matched_keywords']
    #             ]
    #             sheet.append_row(row)
            
    #         print(f"Data successfully uploaded to Google Sheets: {spreadsheet_name}")
            
    #     except Exception as e:
    #         print(f"Error uploading to Google Sheets: {e}")

def main():

    TARGET_KEYWORDS = [
        'SaaS', 'MVP', 'early-stage startup', 'product launch', 'prototype', 'software startup',
        'Artificial Intelligence', 'AI-powered', 'Machine Learning', 'Generative AI', 'NLP',
        'Full-stack development', 'Mobile app', 'MERN stack', 'React Native', 'Next.js', 'Flutter',
        'Automation tools', 'Business automation', 'Workflow automation', 'Zapier alternative',
        'Pre-seed', 'Seed funding', 'B2B SaaS', 'YC-backed', 'Tech startup'
    ]
    


    scraper = IndiegogoScraper(TARGET_KEYWORDS)
    results = scraper.scrape_projects(max_pages=160) 

    scraper.save_to_json('matched_indiegogo_projects2.json')



if __name__ == "__main__":
    main()