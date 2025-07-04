
# Automated Lead-Generation & Outreach System

This repository implements an end-to-end pipeline for:

1. **Discovering** relevant Indiegogo campaigns via their private GraphQL API  
2. **Filtering** campaigns by target keywords  
3. **Scraping** project pages for owner/founder info and location  
4. **Compiling** a JSON of matched leads  
5. **Generating** candidate e-mail permutations  
6. **Verifying** addresses via SMTP “RCPT TO” probes (no real mail sent)  
7. **Falling back** to Selenium-based Google search when SMTP fails  
8. **Handling** CAPTCHA, graceful retries, and progress saving  

---

## Table of Contents

1. [Prerequisites](#prerequisites)  
2. [Installation](#installation)  
3. [Configuration](#configuration)  
4. [Project Discovery](#project-discovery)  
5. [Keyword Filtering](#keyword-filtering)  
6. [Owner & Location Extraction](#owner--location-extraction)  
7. [Lead Compilation](#lead-compilation)  
8. [Email Candidate Generation](#email-candidate-generation)  
9. [SMTP Verification (RCPT Probe)](#smtp-verification-rcpt-probe)  
10. [Catch-All & Greylisting Handling](#catch-all--greylisting-handling)  
11. [Selenium Fallback Search](#selenium-fallback-search)  
12. [CAPTCHA Handling & Retry Logic](#captcha-handling--retry-logic)  
13. [Putting It All Together](#putting-it-all-together)  
14. [Output Files](#output-files)  
15. [Extending & Troubleshooting](#extending--troubleshooting)  

---

## Prerequisites

- **Python 3.10+**  
- **Chrome** browser + matching **Chromedriver**  
- Packages:
  - `requests`
  - `beautifulsoup4`
  - `lxml`
  - `pandas` (optional, for data export)
  - `dnspython`
  - `selenium`
  
Install via:

```bash
pip install requests beautifulsoup4 lxml dnspython selenium

Installation

    Clone this repo:

    git clone https://github.com/yourusername/igg-leadgen.git
    cd igg-leadgen

    Put your Chromedriver binary somewhere on your PATH or note its full path.

Configuration

Edit the constants at the top of each script:

    API credentials (none required for public GraphQL endpoint, but update CSRF token if needed)

    Target keywords array

    Chrome driver path in Selenium script

    Start index / max leads for incremental runs

    Timeouts, retry counts, sleep delays to tune scraping pace

Project Discovery

Script: discover_projects.py

    Hits Indiegogo’s private GraphQL endpoint
    (/private_api/graph/query?operation_id=discoverables_query)

    Paginates until no more results or max_pages reached

    Pulls fields like title, tagline, open_date, clickthrough_url

    Uses a robust parser to extract projects from either the
    discoverables list or nested edges arrays.

Keyword Filtering

Within the same script, after discovery:

    Extract <meta name="keywords"> from each project page

    Normalize and split into a list

    Compare against your TARGET_KEYWORDS array
    (case-insensitive, partial matches allowed)

    Only keep projects where ≥ 1 keyword matches

Owner & Location Extraction

Script: indiegogo_client.py

    Fetch the project page HTML

    Use BeautifulSoup to locate <script> tags containing gon.trust_passport
    & gon.ga_impression_data

    Regex out the JSON blobs; parse to extract:

        owner.name

        owner.linkedin_profile_url

        owner.twitter_profile_url

        ga_impression_data.list → location string

    Return a dict for each project.

Lead Compilation

After discovery & filtering, you end up with matched_projects.json containing:

[
  {
    "title": "...",
    "description": "...",
    "date_opened": "2025-05-08",
    "project_url": "...",
    "matched_keywords": "AI-powered, Mobile app",
    "founder_name": "Jane Doe",
    "linkedin_url": "https://linkedin.com/...",
    "twitter_url": null,
    "location": "Austin, Texas, United States",
    "website_url": "https://janedoestartup.com"
  },
  … 
]

Email Candidate Generation

Script: email_permutations.py

    Read each lead’s founder_name and company domain (from URL)

    Classify name:

        person-full (first + last)

        person-single

        company

    Generate typical patterns:

        first.last@domain

        f.last@domain

        founder@domain, info@domain, etc.

    Store a small list of 8–10 candidates per lead.

SMTP Verification (RCPT Probe)

Script: verify_email.py

    DNS MX lookup via dnspython

    Cache TTLs to avoid repeated DNS queries

    Open SMTP (port 25, fallback 465) with short timeouts

    Send:

    EHLO leadbot.local
    MAIL FROM:<>
    RCPT TO:<candidate@domain>
    QUIT

    Interpret codes:

        250 / 251 → “ok”

        550 → “reject” → stop further guesses

        Timeout / other → retry same port up to 4×, then switch port

    First test a random nonsense address to detect catch-all domains

    Return first ok candidate as verified (or catch-all if random also ok)

Catch-All & Greylisting Handling

    Catch-all detection:
    If 48372@domain returns 250, domain accepts any address

    Greylisting:
    Many hosts defer first connection with a temporary error (4xx).
    Tried to implement:

        Quick probe (1 s timeout) → expected to timeout

        Wait 2 s

        Full probe (3 s timeout) → should now succeed

        But found no real success or a consistent pattern to know 
        when the server was greylisiting. Reverted back to setting 
        the timeout to 8s for each request.

    Retries:
    Up to perPortMaxTries per port before switching ports

Selenium Fallback Search

Script: selenium_email_lookup.py

    For any lead not SMTP-verified, and with email_status ≠ verified, run a Google search:

    "<founder_name>" email OR contact

    Use Selenium:

        Visible Chrome (not headless)

        Randomized user-agent

        Scroll halfway, wait random 3–8 s

    Extract <div class="VwiC3b"> snippets; regex out all e-mails

    Dedupe and store:

        emails: list of hits

        email: first hit or null

        email_status: "found-unverified" or "not-found"

CAPTCHA Handling & Retry Logic

    Wrap each lead’s search in a while True:

        On RuntimeError("Captcha page"):

            Quit current driver

            Wait 8–15 s

            Relaunch Chrome with new UA

            Retry same lead

        After 3 CAPTCHAs → mark email_status = "captcha-skipped" and move on

    Catch Ctrl+C globally to save progress before exit.

Putting It All Together

    discover_projects.py → matched_projects.json

    Merge with any existing leads list → leads.json

    verify_email.py reads matched_projects.json →
    writes matched_verified.json with SMTP results

    selenium_email_lookup.py reads verified.json →
    writes email_enriched.json with any remaining addresses

    Final JSON contains:

    {
      "title": "...",
      "founder_name": "...",
      "location": "...",
      "website_url": "...",
      "email": "jane.doe@company.com",
      "emails": [ "jane.doe@...", "info@..." ],
      "email_status": "verified"    // or catch-all, found-unverified, not-found, captcha-skipped
    }

N8N and email automation:
    
    Finally, the emails were used alongside a small n8n automation script

    Personalized emails were sent to all scraped addresses using n8n
    