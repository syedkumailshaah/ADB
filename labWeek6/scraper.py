# scraper.py
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

URL = "https://papers.nips.cc/paper_files/paper/2024"
OUT_JSON = "papers.json"

def scrape_list_page(url):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # The page contains many <a> tags inside list - adapt if structure changes
    results = []
    # find main list - this page has many <a> items; we will pick links whose href contains '/paper_files/paper/'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "paper_files/paper" in href:
            title = a.get_text(strip=True)
            if not title:
                continue
            link = urljoin(url, href)
            # Authors are usually in the same list item, often the next text or sibling
            # We'll try to find the containing <li> or surrounding text.
            parent = a.parent
            authors_text = ""
            # Try a sibling text node (e.g., following text or in same li)
            if parent:
                # remove the anchor to avoid duplication issues and collect remaining text inside parent
                copy = BeautifulSoup(str(parent), "html.parser")
                for anchor in copy.find_all("a"):
                    anchor.extract()
                authors_text = copy.get_text(" ", strip=True)
            # clean authors_text: remove title repetition if present
            if title in authors_text:
                authors_text = authors_text.replace(title, "").strip(" -–—: ")
            if not authors_text:
                # fallback: look for next sibling
                ns = a.next_sibling
                if ns and isinstance(ns, str):
                    authors_text = ns.strip(" -–—: \n\t")
            results.append({
                "title": title,
                "authors": authors_text,
                "link": link
            })
    # Deduplicate by link
    unique = {}
    for r in results:
        unique[r["link"]] = r
    final = list(unique.values())
    print(f"Scraped {len(final)} papers (unique links). Saving to {OUT_JSON}")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    return final

if __name__ == "__main__":
    scrape_list_page(URL)
