---
name: web-scraping
description: Web scraping with anti-bot bypass, content extraction, undocumented APIs, poison pill detection, and page-change monitoring. Not for clean article-only extraction (use Jina Reader/WebFetch) or myLife clipping (use clip).
---

# Web scraping methodology

Patterns for reliable, ethical web scraping with fallback strategies and anti-bot handling.

Ongoing change monitoring: see [references/monitoring.md](references/monitoring.md).

## Scraping cascade architecture

Multi-strategy extraction with automatic fallback (trafilatura → requests → Playwright stealth, sync + async). Full cascade classes in [references/cascade.py.md](references/cascade.py.md).

## Anti-bot landscape (as of 2026-05)

The cascade above (`requests` → `trafilatura` → Playwright + `playwright-stealth`) handles plain HTML and lightly-protected JS sites. Modern anti-bot stacks (Cloudflare Bot Management / Turnstile, DataDome, Akamai Bot Manager, PerimeterX) layer multiple detection signals: TLS / HTTP-2 fingerprints, browser fingerprints, JS-execution proofs, residential-IP reputation, session behavior. No single tool defeats all of them.

`playwright-stealth` (2.0+, current) patches obvious detection vectors — `navigator.webdriver`, `chrome.runtime`, plugin enumeration, language settings, WebGL fingerprints. Treat it as the floor, not the ceiling. If a target fingerprints TLS or runs Turnstile, stealth alone won't pass.

| Tool | Layer it addresses | Notes |
|---|---|---|
| `curl_cffi` | TLS / HTTP-2 fingerprint | Drop-in replacement for `requests` that mimics Chrome/Safari/Edge JA3+ALPN. Can't run JS — pair with a parsed-HTML extractor when JS isn't required. |
| `playwright-stealth` 2.x | JS-runtime fingerprint | The starting line for Playwright/Chromium. Updates lag the bot stacks; expect to combine with rotation. |
| Camoufox | JS + browser fingerprint at C++ level | Firefox-based stealth browser. Spoofs fingerprint values low enough that JS-side checks can't see through them. Use when Chromium-based stealth is detected. |
| SeleniumBase UC Mode | Turnstile + browser fingerprint | The closest thing to a one-shot Turnstile solver in 2026, but heavier than playwright-stealth. |
| Residential proxy pool | IP reputation | Datacenter IPs (DigitalOcean, AWS) get challenged on first request. Residential pools cost more but bypass the cheapest layer of defense. |

**Use the lightest tool that works.** Targets without aggressive defense don't need Camoufox or proxy pools — `curl_cffi` plus a sleep is usually enough. Reserve heavier tools for sites that explicitly serve a Turnstile challenge or DataDome interstitial.

## Undocumented APIs

### Finding undocumented APIs

Use browser developer tools to discover APIs:

1. **Open developer tools** (right-click → Inspect, or F12)
2. **Go to the Network tab** to monitor all requests
3. **Filter by Fetch/XHR** to show only API calls
4. **Trigger the action** you want to capture (search, scroll, click)
5. **Analyze the response** — usually JSON with key-value pairs
6. **Copy as cURL** (right-click the request)
7. **Convert to code** using [curlconverter.com](https://curlconverter.com/)

### Stripping down API requests

When you copy a cURL from dev tools, it includes many parameters. Strip it down by:

1. **Remove unnecessary cookies** — test without them first
2. **Keep authentication tokens** if required
3. **Identify the input parameters** you can modify (like `prefix` for search terms)
4. **Test parameter values** — some expire, so periodically verify

### Example: Reverse-engineering an autocomplete API

```python
import requests
import time

def search_suggestions(keyword: str) -> dict:
    """
    Get autocompleted search suggestions from an undocumented API.
    Stripped down from browser dev tools capture.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    params = {
        'prefix': keyword,
        'suggestion-type': ['WIDGET', 'KEYWORD'],
        'alias': 'aps',
        'plain-mid': '1',
    }

    response = requests.get(
        'https://completion.amazon.com/api/2017/suggestions',
        params=params,
        headers=headers
    )
    return response.json()

# Collect suggestions for multiple keywords
keywords = ['a', 'b', 'cookie', 'sock']
data = []

for keyword in keywords:
    suggestions = search_suggestions(keyword)
    suggestions['search_word'] = keyword  # track seed keyword
    time.sleep(1)  # rate limit yourself
    data.extend(suggestions.get('suggestions', []))
```
*Source: [Leon Yin, "Finding Undocumented APIs," Inspect Element](https://inspectelement.org/apis.html), 2023*

## Poison pill detection

Detect deliberately corrupted/honeypot content served to scrapers. Detection heuristics and code in [references/poison-pill.md](references/poison-pill.md).

## Social media scraping

Social platforms (YouTube/Instagram/TikTok): use the `youtube-transcript` skill or `agent-reach` instead. Direct scraping of these breaks monthly and risks account bans; prefer official APIs (Meta Content Library, TikTok Research API) for durable access.

## Request patterns

Session reuse, retry/backoff, rate limiting, and header rotation patterns in [references/request-patterns.md](references/request-patterns.md).

## Ethics, robots.txt, and the legal landscape

Scraping is technically simple, ethically nuanced, and legally a moving target. The current state in the US (2026):

**Computer Fraud and Abuse Act (CFAA).** *Van Buren v. United States* (2021) and *hiQ Labs v. LinkedIn* (2022) narrowed the CFAA so that scraping public, non-credentialed pages does NOT constitute "unauthorized access." Logging in (or using credentials), bypassing technical access controls, or scraping after an explicit cease-and-desist letter remains legally fraught. State equivalents (e.g., California's CDAFA) sometimes go further than federal law.

**Terms of service.** Many sites' ToS forbid scraping. ToS is a contract, not a criminal statute — breach exposes you to civil claims (breach of contract, tortious interference, trespass to chattels in some jurisdictions), not jail. The risk profile differs sharply from CFAA.

**robots.txt** is a polite request, not a legal mandate. Ignoring it doesn't make you criminally liable, but courts have cited it as evidence of intent. For journalism in the public interest, that intent can be defensible; for commercial use, it's harder.

**EU GDPR / UK DPA.** If your scraping pulls personal data of EU/UK residents, GDPR/DPA apply regardless of where you run the scraper. Public availability does NOT exempt personal data from these regimes — `Lloyd v. Google` (UK Supreme Court 2021) and CJEU's `Schrems II` lineage make scraping personal data without a lawful basis a real liability.

**Practical baseline:**
- Always read `robots.txt`. Honor crawl delays. Honor `Disallow:`.
- Respect rate limits; add jitter; back off on `429`.
- Don't scrape behind authentication unless you have explicit permission.
- Don't scrape personal data (names, emails, photos) without a lawful basis.
- Identify yourself with a descriptive User-Agent and a contact URL when crawling at volume.
- Cache aggressively to avoid redundant requests.
- Stop if you receive a cease-and-desist or explicit blocking signal — escalating past one is the move that turns a civil dispute into a CFAA case.

**Notes on specific platforms.** Instagram's `instaloader` and TikTok scraping via `yt-dlp` work today but break frequently — Meta and TikTok roll out anti-bot updates monthly. Account bans on the credentials you used are common. For journalism, the official APIs (Meta Content Library, TikTok Research API) are slower but more durable.
