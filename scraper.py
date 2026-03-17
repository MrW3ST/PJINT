import asyncio
import random
import re
from typing import AsyncGenerator

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup

# ── Constantes ─────────────────────────────────────────────────────────────────

BASE_URL = "https://www.pagesjaunes.fr/annuaire/chercherlespros"
HOME_URL = "https://www.pagesjaunes.fr/"

# ── Catégories ─────────────────────────────────────────────────────────────────

_RESTAURATION  = ["restaurant", "brasserie", "pizzeria", "crêperie", "sandwicherie",
                   "kebab", "sushi", "restaurant chinois", "restaurant japonais",
                   "restaurant libanais", "restaurant indien", "fast-food", "rôtisserie",
                   "salon de thé", "bar", "café", "pub", "discothèque"]

_ALIMENTATION  = ["boulangerie", "pâtisserie", "boucherie", "charcuterie", "poissonnerie",
                   "fromager", "épicerie", "épicerie fine", "cave à vins", "chocolatier",
                   "glacier", "traiteur", "primeur", "bio épicerie"]

_SANTE_MEDECIN = ["médecin généraliste", "dermatologue", "cardiologue", "gynécologue",
                   "pédiatre", "radiologue", "pneumologue", "gastro-entérologue",
                   "neurologue", "psychiatre", "ophtalmologue", "rhumatologue",
                   "urologue", "endocrinologue", "allergologue", "gériatre",
                   "chirurgien", "médecin du sport", "sage-femme"]

_SANTE_PARA    = ["dentiste", "orthodontiste", "pharmacie", "kinésithérapeute",
                   "infirmier", "opticien", "audioprothésiste", "podologue",
                   "ostéopathe", "chiropracteur", "psychologue", "orthophoniste",
                   "diététicien", "naturopathe", "acupuncteur", "ergothérapeute",
                   "laboratoire d'analyses médicales", "centre de radiologie"]

_SANTE_ETAB    = ["clinique", "hôpital", "maison de retraite", "EHPAD",
                   "centre médical", "cabinet médical", "centre de rééducation"]

_BEAUTE        = ["coiffeur", "barbier", "esthéticienne", "institut de beauté",
                   "spa", "onglerie", "tatoueur", "piercing", "bronzage",
                   "massage", "hammam", "salon de coiffure"]

_SPORT         = ["salle de sport", "fitness", "musculation", "piscine",
                   "club de tennis", "yoga", "pilates", "danse", "arts martiaux",
                   "boxe", "équitation", "golf", "escalade", "bowling",
                   "karting", "paintball", "laser game", "escape game"]

_HOTELLERIE    = ["hôtel", "camping", "gîte", "chambre d'hôtes",
                   "auberge de jeunesse", "résidence hôtelière", "agence de voyage"]

_EDUCATION     = ["auto-école", "cours particuliers", "soutien scolaire",
                   "crèche", "garderie", "école de musique", "école de danse",
                   "formation professionnelle", "cours de langues", "centre de formation"]

_INFORMATIQUE  = ["réparateur informatique", "réparateur téléphone",
                   "développeur web", "prestataire informatique",
                   "vidéosurveillance", "imprimerie", "photocopie"]

_ARTISANS      = ["plombier", "électricien", "peintre", "menuisier", "maçon",
                   "serrurier", "chauffagiste", "carreleur", "couvreur", "déménageur",
                   "charpentier", "plaquiste", "vitrier", "ferronnier",
                   "climatisation", "ramoneur", "isolation", "façadier",
                   "paysagiste", "jardinier", "pisciniste", "antenniste",
                   "installateur solaire", "ascensoriste", "géomètre"]

_AUTOMOBILE    = ["garage automobile", "carrosserie", "contrôle technique",
                   "pneus", "pare-brise", "dépannage automobile", "lavage auto",
                   "concessionnaire automobile", "moto", "vélo électrique"]

_COMMERCE      = ["fleuriste", "bijouterie", "horlogerie", "librairie",
                   "papeterie", "parfumerie", "vêtements", "chaussures",
                   "électroménager", "meubles", "décoration", "bricolage",
                   "animalerie", "jouets", "sport magasin", "pressing",
                   "cordonnerie", "retouche vêtements", "opticien magasin"]

_SERVICES_PERS = ["aide à domicile", "garde d'enfants", "baby-sitter",
                   "femme de ménage", "repassage à domicile",
                   "auxiliaire de vie", "portage de repas"]

_LIBERALES     = ["avocat", "expert-comptable", "notaire", "huissier",
                   "architecte", "agence de communication", "traducteur",
                   "photographe", "graphiste", "agence de publicité",
                   "conseiller en gestion", "recrutement", "intérim"]

_IMMOBILIER    = ["agence immobilière", "promoteur immobilier",
                   "diagnostiqueur immobilier", "syndic de copropriété",
                   "administrateur de biens", "chasseur immobilier"]

_TRANSPORT     = ["taxi", "VTC", "ambulance", "transport scolaire",
                   "location de voiture", "location de camion",
                   "déménageur", "coursier", "livraison"]

_FUNERAIRE     = ["pompes funèbres", "marbrerie funéraire", "fleuriste funéraire"]

_ANIMAUX       = ["vétérinaire", "animalerie", "toiletteur pour chiens",
                   "pension pour animaux", "dressage canin"]

_LOISIRS       = ["cinéma", "théâtre", "musée", "salle de concert",
                   "parc d'attractions", "casino", "bibliothèque",
                   "galerie d'art", "ludothèque"]

_ALL = (_RESTAURATION + _ALIMENTATION + _SANTE_MEDECIN + _SANTE_PARA +
        _SANTE_ETAB + _BEAUTE + _SPORT + _HOTELLERIE + _EDUCATION +
        _INFORMATIQUE + _ARTISANS + _AUTOMOBILE + _COMMERCE +
        _SERVICES_PERS + _LIBERALES + _IMMOBILIER + _TRANSPORT +
        _FUNERAIRE + _ANIMAUX + _LOISIRS)

KEYWORD_GROUPS: dict[str, list[str]] = {
    "__restauration":  _RESTAURATION,
    "__alimentation":  _ALIMENTATION,
    "__sante_medecin": _SANTE_MEDECIN,
    "__sante_para":    _SANTE_PARA,
    "__sante_etab":    _SANTE_ETAB,
    "__beaute":        _BEAUTE,
    "__sport":         _SPORT,
    "__hotellerie":    _HOTELLERIE,
    "__education":     _EDUCATION,
    "__informatique":  _INFORMATIQUE,
    "__artisans":      _ARTISANS,
    "__automobile":    _AUTOMOBILE,
    "__commerce":      _COMMERCE,
    "__services_pers": _SERVICES_PERS,
    "__liberales":     _LIBERALES,
    "__immobilier":    _IMMOBILIER,
    "__transport":     _TRANSPORT,
    "__funeraire":     _FUNERAIRE,
    "__animaux":       _ANIMAUX,
    "__loisirs":       _LOISIRS,
    "__tout":          _ALL,
}

# ── Stealth ────────────────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
delete navigator.__proto__.webdriver;
window.chrome = {
    runtime: { connect: () => {}, sendMessage: () => {},
                onMessage: { addListener: () => {} },
                getPlatformInfo: (cb) => cb({ os: 'win', arch: 'x86-64' }) },
    loadTimes: () => ({}), csi: () => ({}), app: { isInstalled: false },
};
Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en-US', 'en'] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def resolve_keywords(keyword: str, dynamic_rubriques: list[str] | None = None) -> list[str]:
    kw = keyword.strip()
    if kw == "__tout" and dynamic_rubriques:
        return dynamic_rubriques
    if kw in KEYWORD_GROUPS:
        return KEYWORD_GROUPS[kw]
    return [kw] if kw else []


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        return " ".join(digits[i:i + 2] for i in range(0, 10, 2))
    return raw.strip()


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    for li in soup.select("li.bi"):
        name_el = li.select_one("a[data-pjviewable='1']") or li.select_one("a.bi-denomination")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name:
            continue
        cat_el = (li.select_one(".bi-rubrique") or li.select_one(".activite")
                  or li.select_one("[class*='rubrique']") or li.select_one("[class*='categorie']"))
        if cat_el:
            category = cat_el.get_text(strip=True)
        else:
            first_texts = [t.strip() for t in li.stripped_strings if t.strip()]
            category = first_texts[0] if first_texts and len(first_texts[0]) <= 50 else ""
        address = ""
        for a in li.find_all("a"):
            txt = a.get_text(strip=True)
            if "Voir le plan" in txt:
                address = txt.replace("Voir le plan", "").strip()
                address = re.sub(r"(\d{5})([A-ZÀ-Ÿa-zà-ÿ])", r"\1 \2", address)
                break
        phone = ""
        for text in li.stripped_strings:
            if "Tél" in text:
                m = re.search(r"[\d][\d\s]{8,}", text)
                if m:
                    phone = normalize_phone(m.group(0).strip())
                    break
        if not phone:
            tel_a = li.select_one("a[href^='tel:']")
            if tel_a:
                phone = normalize_phone(tel_a.get("href", "").replace("tel:", ""))
        results.append({"nom": name, "telephone": phone, "adresse": address, "categorie": category})
    return results


def get_total_pages(html: str) -> tuple[int, int]:
    soup = BeautifulSoup(html, "lxml")

    def _pages(n: int) -> int:
        return max(1, (n + 19) // 20)

    nd = soup.find("script", id="__NEXT_DATA__")
    if nd and nd.string:
        for key in ("totalCount", "total_count", "nbResults", "nb_results",
                    "totalHits", "total_hits", "count", "total", "nbPros", "nbAnnonces"):
            m = re.search(rf'"{key}"\s*:\s*(\d+)', nd.string)
            if m:
                total = int(m.group(1))
                if total > 0:
                    return _pages(total), total

    for sel in [".nb-results-count", ".bi-nbresults", "[class*='nbresults']",
                "[class*='nb-results']", "[class*='results-count']"]:
        el = soup.select_one(sel)
        if el:
            raw = el.get_text().replace("\xa0", "").replace("\u202f", "").replace(" ", "")
            m = re.search(r"(\d+)", raw)
            if m:
                total = int(m.group(1))
                if total > 0:
                    return _pages(total), total

    text_clean = soup.get_text().replace("\xa0", " ").replace("\u202f", " ")
    m = re.search(r"(\d[\d\s]{0,9})\s*(résultat|établissement|annonce|entreprise)", text_clean, re.I)
    if m:
        total_str = re.sub(r"\s", "", m.group(1))
        if total_str:
            total = int(total_str)
            if total > 0:
                return _pages(total), total

    max_page = 1
    for link in soup.select("a[href*='page='], [class*='pagination'] a"):
        href = link.get("href", "")
        pm = re.search(r"[?&]page=(\d+)", href)
        if pm:
            max_page = max(max_page, int(pm.group(1)))
        txt = link.get_text(strip=True)
        if txt.isdigit():
            max_page = max(max_page, int(txt))
    return max_page, 0


def is_blocked(html: str) -> bool:
    low = html.lower()
    return any(s in low for s in [
        "datadome", "vous avez été bloqué", "accès refusé",
        "access denied", "too many requests",
        "challenge-platform", "challenge-form", "turnstile",
    ])


async def make_context(browser: Browser) -> BrowserContext:
    ctx = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1920, "height": 1080},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9", "DNT": "1"},
    )
    await ctx.add_init_script(STEALTH_JS)
    return ctx


async def goto_and_wait(page: Page, url: str, delay: float = 2.0) -> str:
    await page.goto(url, wait_until="networkidle", timeout=60_000)
    await asyncio.sleep(delay + random.uniform(0, 1.0))
    return await page.content()


async def fetch_rubriques_pj(ville: str) -> list[str]:
    rubriques: list[str] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled", "--lang=fr-FR"],
            )
            ctx = await make_context(browser)
            tab = await ctx.new_page()
            await goto_and_wait(tab, HOME_URL, delay=1.5)
            url = f"https://www.pagesjaunes.fr/annuaire/{ville.lower().replace(' ', '-')}"
            html = await goto_and_wait(tab, url, delay=3.0)
            await browser.close()
        soup = BeautifulSoup(html, "lxml")
        seen = set()
        skip = ["voir", "plus", "résultat", "page", "suivant", "précédent",
                "accueil", "connexion", "inscription", "aide", "contact",
                "mentions", "cgv", "cookies", "pagesjaunes"]
        for a in soup.find_all("a", href=True):
            txt = a.get_text(strip=True)
            href = a.get("href", "")
            if not txt or len(txt) < 3 or len(txt) > 60:
                continue
            if any(c.isdigit() for c in txt):
                continue
            if any(w in txt.lower() for w in skip):
                continue
            if "/annuaire/" in href and txt.lower() not in seen:
                seen.add(txt.lower())
                rubriques.append(txt)
    except Exception:
        pass
    return rubriques if len(rubriques) >= 20 else list(_ALL)


# ── Générateur principal (yield de dicts) ──────────────────────────────────────

async def scrape(
    ville: str,
    keyword: str,
    start_page: int = 1,
) -> AsyncGenerator[dict, None]:
    """
    Générateur async qui yield des dicts d'événements :
      {"type": "status",        "msg": str}
      {"type": "info",          "total_pages": int, "total_results": int, ...}
      {"type": "results",       "page": int, "items": list, "total_found": int, ...}
      {"type": "error"|"warn",  "msg": str}
      {"type": "done",          "total": int}
    """
    dynamic_rubriques = None
    if keyword.strip() == "__tout":
        yield {"type": "status", "msg": "Récupération des rubriques PagesJaunes…"}
        dynamic_rubriques = await fetch_rubriques_pj(ville)
        yield {"type": "status", "msg": f"{len(dynamic_rubriques)} rubriques trouvées. Démarrage…"}

    keywords = resolve_keywords(keyword, dynamic_rubriques)
    all_results: list[dict] = []

    if not keywords:
        yield {"type": "error", "msg": "Aucun mot-clé fourni."}
        return

    yield {"type": "status", "msg": "Démarrage du navigateur…"}

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled", "--disable-gpu",
                    "--window-size=1920,1080", "--disable-extensions",
                    "--disable-infobars", "--disable-background-networking",
                    "--disable-default-apps", "--no-first-run", "--lang=fr-FR",
                ],
            )
            ctx = await make_context(browser)
            tab = await ctx.new_page()

            yield {"type": "status", "msg": "Chargement de la page d'accueil…"}
            try:
                await goto_and_wait(tab, HOME_URL, delay=2.0)
            except Exception as e:
                yield {"type": "warn", "msg": f"Homepage : {e}"}

            total_keywords = len(keywords)
            for kw_idx, kw in enumerate(keywords):
                page        = start_page if kw_idx == 0 else 1
                total_pages = 1
                seen_keys: set[str] = set()

                yield {
                    "type":      "keyword_start",
                    "keyword":   kw,
                    "kw_index":  kw_idx + 1,
                    "kw_total":  total_keywords,
                    "ville":     ville,
                }

                while True:
                    url = f"{BASE_URL}?quoiqui={kw}&ou={ville}&page={page}&nb=50"
                    try:
                        html = await goto_and_wait(tab, url, delay=2.5)
                    except Exception as e:
                        yield {"type": "error", "msg": f"Navigation ({kw}, p.{page}) : {e}"}
                        break

                    if is_blocked(html):
                        yield {"type": "error", "msg": "Blocage détecté (Cloudflare). Réessayez plus tard."}
                        await browser.close()
                        return

                    if page == start_page or page == 1:
                        try:
                            total_results = await tab.evaluate("""() => {
                                const d = window.__NEXT_DATA__;
                                if (!d) return 0;
                                const s = JSON.stringify(d);
                                const m = s.match(/"(?:totalCount|total_count|nbResults|nb_results|totalHits|nbPros|nbAnnonces|count|total)"\\s*:\\s*(\\d+)/);
                                return m ? parseInt(m[1]) : 0;
                            }""")
                        except Exception:
                            total_results = 0

                        total_pages, total_fallback = get_total_pages(html)
                        if not total_results:
                            total_results = total_fallback

                        yield {
                            "type":          "info",
                            "total_pages":   total_pages,
                            "total_results": total_results,
                            "ville":         ville,
                            "keyword":       kw,
                        }

                    page_results = parse_page(html)
                    if not page_results:
                        break

                    page_keys = {f"{r['nom']}|{r['telephone']}" for r in page_results}
                    if page_keys and page_keys.issubset(seen_keys):
                        break
                    seen_keys.update(page_keys)

                    all_results.extend(page_results)
                    yield {
                        "type":        "results",
                        "page":        page,
                        "total_pages": total_pages,
                        "items":       page_results,
                        "total_found": len(all_results),
                        "keyword":     kw,
                    }

                    page += 1
                    await asyncio.sleep(random.uniform(3.0, 5.5))

                if kw_idx < total_keywords - 1:
                    await asyncio.sleep(random.uniform(2.0, 4.0))

            await browser.close()

    except Exception as exc:
        yield {"type": "error", "msg": f"Erreur Playwright : {exc}"}

    yield {"type": "done", "total": len(all_results)}
