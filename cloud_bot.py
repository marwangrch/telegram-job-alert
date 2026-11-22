import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

# --- ENVIRONMENT SECRETS ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

BASE_DIR = Path(__file__).parent
SEEN_FILE = BASE_DIR / "seen_jobs.json"
SEARCH_CONFIG_FILE = BASE_DIR / "search_config.json"

CONTRACT_TYPE_MAP = {
    "internship": "I",   # Stage / Alternance
    "full_time": "F",    # CDI / Temps plein
    "contract": "C",     # CDD / Freelance / Contrat
    "part_time": "P",    # Temps partiel
    "temporary": "T",    # Intérim / Temporaire
    "any": "",           # Tous types de contrats
}

TIME_WINDOW_MAP = {
    "24h": "r86400",
    "3d": "r259200",
    "7d": "r604800",
    "30d": "r2592000",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def load_search_config():
    if SEARCH_CONFIG_FILE.exists():
        return json.loads(SEARCH_CONFIG_FILE.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Missing configuration file: {SEARCH_CONFIG_FILE}")


def load_seen():
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")).get("seen_job_ids", []))
        except Exception:
            return set()
    return set()


def save_seen(seen_set):
    SEEN_FILE.write_text(
        json.dumps({"seen_job_ids": sorted(list(seen_set))}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def fetch_url(url, retries=3, backoff=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
            print(f"HTTP error {e.code} on {url}")
            return None
        except Exception as e:
            print(f"Request error on {url}: {e}")
            return None
    return None


def search_linkedin_jobs(keywords, location, contract_code="I", time_filter="r604800"):
    params_dict = {
        "keywords": keywords,
        "location": location,
        "f_TPR": time_filter,
        "sortBy": "DD",
        "start": 0,
    }
    if contract_code:
        params_dict["f_JT"] = contract_code

    params = urllib.parse.urlencode(params_dict)
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{params}"
    raw_html = fetch_url(url)
    if not raw_html:
        return []

    soup = BeautifulSoup(raw_html, "html.parser")
    jobs = []
    for card in soup.find_all("div", class_="base-card"):
        urn = card.get("data-entity-urn", "")
        job_id = urn.split(":")[-1] if ":" in urn else None
        if not job_id:
            link_tag = card.find("a", class_="base-card__full-link")
            if link_tag and link_tag.get("href"):
                m = re.search(r"-(\d+)(?:\?|$)", link_tag["href"])
                if m:
                    job_id = m.group(1)
        if not job_id:
            continue

        title_el = card.find("h3", class_="base-search-card__title")
        company_el = card.find("h4", class_="base-search-card__subtitle")
        loc_el = card.find("span", class_="job-search-card__location")
        link_el = card.find("a", class_="base-card__full-link")

        title = title_el.get_text(strip=True) if title_el else "Sans titre"
        company = company_el.get_text(strip=True) if company_el else "Entreprise inconnue"
        loc = loc_el.get_text(strip=True) if loc_el else location
        link = link_el["href"].split("?")[0] if (link_el and link_el.get("href")) else f"https://www.linkedin.com/jobs/view/{job_id}/"

        jobs.append({
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": loc,
            "url": link,
        })
    return jobs


def get_job_description(job_id):
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    raw_html = fetch_url(url)
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    desc_el = soup.find("div", class_="show-more-less-html__markup") or soup.find("div", class_="description__text")
    if not desc_el:
        return ""
    return desc_el.get_text(separator="\n", strip=True)


def matches_filters(job, description, cfg):
    title_lower = job["title"].lower()
    desc_lower = description.lower()

    required = [k.lower() for k in cfg.get("required_keywords_in_offer", [])]
    excluded = [k.lower() for k in cfg.get("excluded_keywords_in_title", [])]

    if required:
        keywords_ok = any(k in title_lower or k in desc_lower for k in required)
    else:
        keywords_ok = True

    if excluded:
        excluded_hit = any(k in title_lower for k in excluded)
    else:
        excluded_hit = False

    return keywords_ok and not excluded_hit


def summarize_with_gemini(job, description, cfg):
    if not GEMINI_API_KEY or not description:
        short_desc = description[:700] + ("..." if len(description) > 700 else "")
        return short_desc if short_desc else "Description non disponible sur l'aperçu."

    context = cfg.get("gemini_context", "un candidat recherchant des offres pertinentes")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        f"Tu es un assistant carrière qui résume des offres d'emploi pour {context}.\n"
        f"Titre: {job['title']}\nEntreprise: {job['company']}\nLieu: {job['location']}\n"
        f"Description complète:\n{description[:4000]}\n\n"
        f"Fais un résumé en français de 4-5 lignes maximum : missions principales, compétences/stack technique, "
        f"et précise le type de contrat, la durée ou les dates si elles sont mentionnées."
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return description[:700] + ("..." if len(description) > 700 else "")


def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables!")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    if len(text) > 4000:
        text = text[:3990] + "\n..."
    payload = json.dumps({
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    cfg = load_search_config()
    seen = load_seen()
    all_candidates = {}

    contract_code = CONTRACT_TYPE_MAP.get(cfg.get("contract_type", "internship"), "")
    time_filter = TIME_WINDOW_MAP.get(cfg.get("time_window", "7d"), "r604800")
    max_offers = int(cfg.get("max_offers_per_run", 10))

    for q in cfg.get("queries", []):
        print(f"Searching: {q['keywords']} in {q['location']}...")
        found = search_linkedin_jobs(
            q["keywords"],
            q["location"],
            contract_code=contract_code,
            time_filter=time_filter,
        )
        for job in found:
            if job["job_id"] not in seen and job["job_id"] not in all_candidates:
                all_candidates[job["job_id"]] = job
        time.sleep(3)

    print(f"Found {len(all_candidates)} new candidate jobs.")
    new_offers_to_send = []

    for job_id, job in list(all_candidates.items())[:max_offers]:
        time.sleep(2)
        desc = get_job_description(job_id)
        if matches_filters(job, desc, cfg):
            job["summary"] = summarize_with_gemini(job, desc, cfg)
            new_offers_to_send.append(job)
        seen.add(job_id)

    alert_title = cfg.get("alert_title", "NOUVELLE(S) OFFRE(S) D'EMPLOI")
    sector_label = cfg.get("sector_label", "France")
    target_label = cfg.get("target_label", "Toutes opportunités")

    if not new_offers_to_send:
        send_telegram_message(
            f"📭 Bonjour ! Aucune nouvelle offre ({alert_title} - {sector_label}) "
            f"n'a été publiée depuis la dernière vérification."
        )
    else:
        header = (
            f"🎯 {len(new_offers_to_send)} {alert_title}\n"
            f"📍 Secteur : {sector_label}\n"
            f"🎓 Cible : {target_label}\n"
        )
        send_telegram_message(header)
        for idx, offer in enumerate(new_offers_to_send, 1):
            msg = (
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{idx}️⃣ {offer['title']}\n"
                f"🏢 Entreprise : {offer['company']}\n"
                f"📍 Lieu : {offer['location']}\n\n"
                f"📝 Description :\n{offer['summary']}\n\n"
                f"🔗 Lien : {offer['url']}"
            )
            send_telegram_message(msg)
            time.sleep(1)

    save_seen(seen)
    print("Done!")


if __name__ == "__main__":
    main()
