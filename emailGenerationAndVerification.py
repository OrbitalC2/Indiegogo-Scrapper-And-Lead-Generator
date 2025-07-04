import re, random, time, smtplib, socket, ssl, json, os
from typing import List, Dict, Set
import dns.resolver
from urllib.parse import urlparse


genericRoles = [
    "founder@", "ceo@", "contact@", "info@", "hello@",
    "team@", "support@", "admin@", "enquiries@",
]
perPermutationMaxTries = 4              
socketTimeout   = 8              
commonNames = "listOfHumanNames.txt"     


def loadFirstNames(path: str = commonNames) -> Set[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            return {line.strip().lower() for line in fh if line.strip()}
    except FileNotFoundError:
        print(f"[WARN] '{path}' not found – continuing with empty name list")
        return set()

firstNames = loadFirstNames()

def splitName(name: str):
    parts = name.strip().split()
    return (parts[0].lower(), parts[-1].lower()) if parts else ("", "")

def patternsForPerson(first: str, last: str, domain: str) -> List[str]:
    f = first[:1]
    return [
        f"{first}.{last}@{domain}", f"{first}{last}@{domain}",
        f"{f}.{last}@{domain}",     f"{f}{last}@{domain}",
        f"{first}@{domain}",        f"{last}@{domain}",
        f"{first}_{last}@{domain}", f"{f}_{last}@{domain}",
    ]

def patternsSingle(first: str, domain: str) -> List[str]:
    f = first[:1]
    return [f"{first}@{domain}", f"{f}@{domain}", *[role + domain for role in genericRoles]]

def patternsCompany(domain: str) -> List[str]:
    return [role + domain for role in genericRoles]


splitRegex = re.compile(r"\s*(?:\+|&|/| and )\s*", flags=re.I)

def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("＆", "&").strip())

#in the case of founder a + founder b
def splitCollab(name: str) -> List[str]:
    return [p for p in splitRegex.split(name) if p]

def token_stats(tokens: List[str]):
    containsSymbol = any(re.search(r"[^A-Za-z]", tok) for tok in tokens)
    containsFirstName  = any(tok.lower() in firstNames for tok in tokens)
    ContainsAllCaps   = all(tok.isupper() and len(tok) > 2 for tok in tokens)
    return containsSymbol, containsFirstName, ContainsAllCaps

def classify_piece(piece: str) -> str:

    tokens = piece.split()
    containsSymbol, containsFirstName, ContainsAllCaps = token_stats(tokens)

    # ── apply the same rules as before ──────────────────────────────
    if containsSymbol or ContainsAllCaps:
        label = "company"
    elif len(tokens) == 1:
        label = "person-single" if containsFirstName else "company"
    elif tokens[-1].lower() in {
        # ── legal designators ───────────────────────────────────────────
        "llc","ltd","inc","corp","co","plc","gmbh","ag","kg","bv","nv","oy",
        "ab","sas","sarl","srl","spa","pte","pty","kk","oyj","kft","as","aps",
        "sa","sl","sgps","spzoo","zrt","llp","lp","oop","gbr","ltda",
        # ── financial / holding / venture terms ────────────────────────
        "holdings","holding","ventures","capital","investments","partners",
        "group","fund","trust","management","advisors","associates",
        # ── tech / professional services ───────────────────────────────
        "tech","technology","technologies","systems","solutions","services",
        "software","digital","analytics","engineering","consulting",
        "networks","communications","security",
        # ── creative / media / consumer products ───────────────────────
        "studio","studios","labs","lab","design","designs","works",
        "media","creative","production","productions","pictures","films",
        "records","music","games","gaming","brands","products",
        # ── industrial / retail / misc. ────────────────────────────────
        "industries","industrial","manufacturing","factory","brewing",
        "brewery","foods","beverages","pharma","medical","biotech",
        "devices","robotics","outdoors","solutions","consultants",
    }:
        label = "company"
    elif containsFirstName:
        label = "person-full"
    else:
        label = "company"

   
    print(f"[CLASSIFY] '{piece}' → {label}")
    return label


def collectCandidates(displayName: str, domain: str) -> List[str]:
    pieces = splitCollab(normalize(displayName))
    combos: List[str] = []

    for piece in pieces:
        label = classify_piece(piece)
        first, last = splitName(piece)

        if label == "person-full":
            combos += patternsForPerson(first, last, domain)
        elif label == "person-single":
            combos += patternsSingle(first, domain)
        elif label == "company":
            combos += patternsCompany(domain)
        else: # ambiguous
            combos += patternsForPerson(first, last, domain)
            combos += patternsCompany(domain)

   
    seen, unique = set(), []
    for addr in combos:
        if addr not in seen:
            unique.append(addr)
            seen.add(addr)
    return unique

def mx_hosts(domain: str) -> List[str]:
    print(f"[DNS] lookup {domain}")
    try:
        ans = dns.resolver.resolve(domain, "MX")
        hosts = sorted((r.preference, r.exchange.to_text().rstrip(".")) for r in ans)
        hosts = [h[1] for h in hosts]
        print(f"[DNS] MX hosts → {hosts}")
        return hosts
    except Exception as e:
        print(f"[DNS] failed ({e})")
        return []

#trying port 25 and 465(fallback) as they are most used
def SMPT_RCPT(host: str, addr: str, timeout=socketTimeout):
    """
    return "ok" | "reject" | "error"
    """
    ports = (25, 465)
    for port in ports:
        for attempt in range(1, perPermutationMaxTries + 1):
            tag = f"[SMTP {host}:{port} t{attempt}/{perPermutationMaxTries}]"
            try:
                connection = (smtplib.SMTP(host, port, timeout=timeout)
                        if port == 25 else
                        smtplib.SMTP_SSL(host, port, timeout=timeout,
                                         context=ssl.create_default_context()))
                connection.helo("leadbot.local")
                connection.mail("")
                code, _ = connection.rcpt(addr)
                connection.quit()

                if code in (250, 251):
                    print(f"{tag} {addr} → {code}")
                    return "ok"
                if code == 550:
                    print(f"{tag} 550 user unknown")
                    return "reject"
                print(f"{tag} other {code}")

            except (socket.timeout, OSError, smtplib.SMTPException):
                print(f"{tag} timeout/error")
        # give up on this port, move to next
    return "error"

def verifyCandidate(cands: List[str], mx_list: List[str]) -> Dict[str, str]:
    if not mx_list:
        return {"email": None, "status": "no-mx"}

    mx = mx_list[0]
    print(f"[VERIFY] MX {mx}")

    nonsense = f"{random.randint(1000,9999)}@{cands[0].split('@')[1]}"
    catch_all = SMPT_RCPT(mx, nonsense) == "ok"

    for addr in cands:
        res = SMPT_RCPT(mx, addr)
        if res == "ok":
            status = "catch-all" if catch_all else "verified"
            print(f"[FOUND] {addr} ({status})")
            return {"email": addr, "status": status}
        if res == "reject":
            print("[STOP] 550 – aborting permutations")
            break

    print("[FOUND] none")
    return {"email": None,
            "status": "catch-all" if catch_all else "not-found"}


def findBestEmail(displayName: str, company_domain: str) -> Dict[str, str]:
    print(f"\n=== {displayName} @ {company_domain} ===")
    cands = collectCandidates(displayName, company_domain)
    print(f"[CANDIDATES] {len(cands)} addresses to test")
    return verifyCandidate(cands, mx_hosts(company_domain))


def extractDomainFromURL(url: str) -> str:
    net = urlparse(url).netloc.lower()
    if net.startswith("www."):
        net = net[4:]
    return net.split(":")[0]

#writes back progress after full execution (intentional)
#if you want to write back after a ctrl-c use SIGINT
def enrichLeads(path: str = "final.json"):
   
    if not os.path.exists(path):
        print(f"[ERROR] '{path}' not found")
        return
    with open(path, encoding="utf-8") as fh:
        leads = json.load(fh)

    updated = 0
    progressCount = 1
    for lead in leads:
        print(f"\nCLASSIFYING LEAD NUMBER {progressCount}")
        founder = lead.get("founder_name")
        url = lead.get("website_url")
        if not url:
            lead["email"] = None
            lead["email_status"] = "skipped"
            print("   --\nSKIPPING. No website for founder {founder}.")
            progressCount += 1
            continue

        domain = extractDomainFromURL(url)
        result = findBestEmail(founder, domain)
        lead["email"] = result["email"]
        lead["email_status"] = result["status"]
        updated += 1
        progressCount += 1
      
        time.sleep(0.5)

   
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(leads, fh, indent=2, ensure_ascii=False)
    print(f"[DONE] processed {updated} leads → '{path}' updated")


if __name__ == "__main__":
    enrichLeads()

