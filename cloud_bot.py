import json
import os
import re
import time
import html
import urllib.request
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

SEEN_FILE = Path(__file__).parent / "seen_jobs.json"

SEARCH_QUERIES = [
    {"keywords": "Stage Data Engineer", "location": "Paris"},
    {"keywords": "Stage Machine Learning Engineer", "location": "Paris"},
    {"keywords": "Stage AI Engineer", "location": "Paris"},
    {"keywords": "Stage Data Engineer", "location": "La Défense"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}


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


def search_linkedin_jobs(keywords, location, time_filter="r86400"):
    """
    time_filter: r86400 (24h), r604800 (7d)
    f_JT=I (Internship)
    """
    params = urllib.parse.urlencode({
        "keywords": keywords,
        "location": location,
        "f_TPR": time_filter,
        "f_JT": "I",
        "sortBy": "DD",
        "start": 0,
    })
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


def is_internship_offer(job, description):
    title_lower = job["title"].lower()
    desc_lower = description.lower()
    keywords_ok = any(k in title_lower or k in desc_lower for k in ["stage", "stagiaire", "intern", "internship"])
    # Exclude obvious senior roles
    senior_exclude = any(k in title_lower for k in ["senior", "lead", "directeur", "manager", "cdi"])
    return keywords_ok and not senior_exclude


def summarize_with_gemini(job, description):
    """Optional: if GEMINI_API_KEY is set, creates a clean summary and checks 10-week / summer compatibility."""
    if not GEMINI_API_KEY or not description:
        short_desc = description[:700] + ("..." if len(description) > 700 else "")
        return short_desc if short_desc else "Description non disponible sur l'aperçu."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        f"Tu es un assistant qui résume des offres de stage pour un étudiant en 4ème année d'école d'ingénieur "
        f"cherchant un stage de Data/ML/AI Engineer à Paris/La Défense d'environ 10 semaines (entre le 27 juin et le 15 septembre).\n"
        f"Titre: {job['title']}\nEntreprise: {job['company']}\nLieu: {job['location']}\n"
        f"Description complète:\n{description[:4000]}\n\n"
        f"Fais un résumé en français de 4-5 lignes maximum : missions principales, stack technique, et précise la durée/dates du stage si elles sont mentionnées."
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
    seen = load_seen()
    all_candidates = {}

    # Search 7 days window to make sure we don't miss weekend/recent posts, deduplicated by seen_jobs.json
    for q in SEARCH_QUERIES:
        print(f"Searching: {q['keywords']} in {q['location']}...")
        found = search_linkedin_jobs(q["keywords"], q["location"], time_filter="r604800")
        for job in found:
            if job["job_id"] not in seen and job["job_id"] not in all_candidates:
                all_candidates[job["job_id"]] = job
        time.sleep(3)  # Politeness delay to avoid LinkedIn 429

    print(f"Found {len(all_candidates)} new candidate jobs.")
    new_offers_to_send = []

    for job_id, job in list(all_candidates.items())[:10]:  # Process up to 10 new offers per day
        time.sleep(2)
        desc = get_job_description(job_id)
        if is_internship_offer(job, desc):
            summary = summarize_with_gemini(job, desc)
            job["summary"] = summary
            new_offers_to_send.append(job)
        # Mark as seen either way so we don't re-fetch non-matching offers tomorrow
        seen.add(job_id)

    if not new_offers_to_send:
        send_telegram_message(
            "📭 Bonjour ! Aucune nouvelle offre de stage (Data / ML / AI Engineer à Paris & La Défense) "
            "n'a été publiée depuis la dernière vérification."
        )
    else:
        header = (
            f"🎯 {len(new_offers_to_send)} NOUVELLE(S) OFFRE(S) DE STAGE (Data / ML / AI)\n"
            f"📍 Secteur : Paris / La Défense & alentours\n"
            f"🎓 Cible : Stage 4A Ingénieur (~10 sem., 27 juin - 15 sept.)\n"
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
