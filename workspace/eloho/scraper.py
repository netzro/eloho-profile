"""
ngx_scraper.py — NGX stock scraper (afx.kwayisi.org)
Extracts complete stock data including price, trading info, performance, valuation, and company profile
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

# ============================================================================
# CONSTANTS
# ============================================================================

SCRAPER_BASE_URL = "https://afx.kwayisi.org/ngx"
WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

# ============================================================================
# PRIVATE HELPER FUNCTIONS
# ============================================================================

def _fetch(url: str, max_retries: int = 2) -> Optional[requests.Response]:
    """Fetch a URL with retry logic and polite delays."""
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(random.uniform(1, 2))
            resp = requests.get(url, headers=WEB_HEADERS, timeout=10)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            if len(resp.text) > 500:
                return resp
        except Exception:
            if attempt == max_retries - 1:
                raise
    return None


def _parse_volume(volume_str: str) -> int:
    """Parse volume string with suffixes (M, B, Tr) to integer."""
    if not volume_str:
        return 0
    volume_str = volume_str.strip().upper()
    match = re.match(r"([\d,]+\.?\d*)\s*([A-Za-z]*)", volume_str)
    if not match:
        return 0
    numeric_part = float(match.group(1).replace(",", ""))
    suffix = match.group(2)
    if suffix == "M":
        return int(round(numeric_part * 1_000_000))
    elif suffix == "B":
        return int(round(numeric_part * 1_000_000_000))
    elif suffix == "TR" or suffix == "T":
        return int(round(numeric_part * 1_000_000_000_000))
    else:
        return int(round(numeric_part))


def _parse_percentage(pct_str: str) -> float:
    """Parse percentage string to float."""
    if not pct_str:
        return 0.0
    match = re.search(r"([+-]?[\d.]+)%", pct_str)
    if match:
        return float(match.group(1))
    return 0.0


def _parse_large_number(num_str: str) -> float:
    """Parse large numbers with T, B, M suffixes."""
    if not num_str:
        return 0.0
    num_str = num_str.strip().upper()
    match = re.match(r"([\d,]+\.?\d*)\s*([TBM]?)", num_str)
    if not match:
        return 0.0
    value = float(match.group(1).replace(",", ""))
    suffix = match.group(2)
    if suffix == "T":
        return value * 1_000_000_000_000
    elif suffix == "B":
        return value * 1_000_000_000
    elif suffix == "M":
        return value * 1_000_000
    else:
        return value


# ============================================================================
# MAIN SCRAPING FUNCTION
# ============================================================================

def ngx_scrape_stock(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Scrape complete stock data for a single NGX symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., "UBA", "GTCO", "ACCESSCORP")
    
    Returns:
        Dictionary with keys:
        - Basic: symbol, price, day_high, day_low, volume, open, deals, turnover
        - Performance: perf_1wk, perf_4wk, perf_3mo, perf_6mo, perf_1yr, perf_ytd
        - Valuation: eps, pe_ratio, dividend_per_share, dividend_yield, shares_outstanding, market_cap
        - Profile: sector, industry, founded, employees, address, telephone, email, website
        - Rankings: value_rank, value_pct, traded_rank
        - Statistics: prev_close, change_abs, change_pct, year_start, ytd_gain
    """
    resp = _fetch(f"{SCRAPER_BASE_URL}/{symbol.lower()}.html")
    if not resp:
        return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Initialize data dictionary
    data = {
        "symbol": symbol.upper(),
        "price": 0.0,
        "day_high": 0.0,
        "day_low": 0.0,
        "volume": 0,
        "open": 0.0,
        "deals": 0,
        "turnover": 0.0,
        "perf_1wk": 0.0,
        "perf_4wk": 0.0,
        "perf_3mo": 0.0,
        "perf_6mo": 0.0,
        "perf_1yr": 0.0,
        "perf_ytd": 0.0,
        "eps": 0.0,
        "pe_ratio": 0.0,
        "dividend_per_share": 0.0,
        "dividend_yield": 0.0,
        "shares_outstanding": 0.0,
        "market_cap": 0.0,
        "sector": "",
        "industry": "",
        "founded": "",
        "employees": 0,
        "address": "",
        "telephone": "",
        "email": "",
        "website": "",
        "value_rank": 0,
        "value_pct": 0.0,
        "traded_rank": 0,
        "prev_close": 0.0,
        "change_abs": 0.0,
        "change_pct": 0.0,
        "year_start": 0.0,
        "ytd_gain": 0.0,
    }
    
    # ========================================================================
    # 1. EXTRACT FROM "Last Trading Results" AND "Growth & Valuation" TABLES
    # ========================================================================
    
    for div in soup.find_all("div", class_="t"):
        tables = div.find_all("table")
        for table in tables:
            header_row = table.find("th", colspan="2")
            if not header_row:
                continue
            
            header_text = header_row.get_text()
            table_text = table.get_text(strip=True)
            
            # Process Last Trading Results table
            if "Last Trading Results" in header_text:
                low_match = re.search(r"Day['’]s Low Price([\d,]+\.?\d*)", table_text, re.IGNORECASE)
                if low_match:
                    data["day_low"] = float(low_match.group(1).replace(",", ""))
                
                high_match = re.search(r"Day['’]s High Price([\d,]+\.?\d*)", table_text, re.IGNORECASE)
                if high_match:
                    data["day_high"] = float(high_match.group(1).replace(",", ""))
                
                volume_match = re.search(r"Traded Volume([\d,]+\.?\d*)([MBT]?)", table_text, re.IGNORECASE)
                if volume_match:
                    value = volume_match.group(1) + (volume_match.group(2) if volume_match.group(2) else "")
                    data["volume"] = _parse_volume(value)
                
                deals_match = re.search(r"Number of Deals([\d,]+)", table_text, re.IGNORECASE)
                if deals_match:
                    data["deals"] = int(deals_match.group(1).replace(",", ""))
                
                turnover_match = re.search(r"Gross Turnover([\d,]+\.?\d*)([MBT]?)", table_text, re.IGNORECASE)
                if turnover_match:
                    value = turnover_match.group(1) + (turnover_match.group(2) if turnover_match.group(2) else "")
                    data["turnover"] = _parse_volume(value)
                
                open_match = re.search(r"Opening Price(?:[\s]*)([\d,]+\.?\d*)?", table_text, re.IGNORECASE)
                if open_match and open_match.group(1):
                    data["open"] = float(open_match.group(1).replace(",", ""))
            
            # Process Growth & Valuation table
            elif "Growth" in header_text:
                shares_match = re.search(r"Shares Outstanding([\d,]+\.?\d*)([TBM]?)", table_text, re.IGNORECASE)
                if shares_match:
                    value = shares_match.group(1) + (shares_match.group(2) if shares_match.group(2) else "")
                    data["shares_outstanding"] = _parse_large_number(value)
                
                mcap_match = re.search(r"Market Capitalization([\d,]+\.?\d*)([TBM]?)", table_text, re.IGNORECASE)
                if mcap_match:
                    value = mcap_match.group(1) + (mcap_match.group(2) if mcap_match.group(2) else "")
                    data["market_cap"] = _parse_large_number(value)
                
                eps_match = re.search(r"Earnings Per Share([\d,]+\.?\d*)", table_text, re.IGNORECASE)
                if eps_match:
                    data["eps"] = float(eps_match.group(1).replace(",", ""))
                
                pe_match = re.search(r"Price/Earning Ratio([\d,]+\.?\d*)", table_text, re.IGNORECASE)
                if pe_match:
                    data["pe_ratio"] = float(pe_match.group(1).replace(",", ""))
                
                dps_match = re.search(r"Dividend Per Share([\d,]+\.?\d*)", table_text, re.IGNORECASE)
                if dps_match:
                    data["dividend_per_share"] = float(dps_match.group(1).replace(",", ""))
                
                dy_match = re.search(r"Dividend Yield([\d,]+\.?\d*%)", table_text, re.IGNORECASE)
                if dy_match:
                    data["dividend_yield"] = _parse_percentage(dy_match.group(1))
    
    # ========================================================================
    # 2. EXTRACT CURRENT PRICE AND CHANGE FROM HEADER
    # ========================================================================
    
    price_div = soup.find("div", class_="h2")
    if price_div:
        # Extract price from inline-block span
        price_span = price_div.find("span", style=lambda x: x and "inline-block" in x)
        if price_span:
            span_text = price_span.get_text()
            price_match_num = re.search(r'([\d,]+\.?\d*)', span_text)
            if price_match_num:
                data["price"] = float(price_match_num.group(1).replace(",", ""))
        
        # Fallback: regex on div text
        if data["price"] == 0.0:
            div_text = price_div.get_text()
            price_match = re.search(r'•\s*([\d,]+\.?\d*)', div_text)
            if not price_match:
                price_match = re.search(r'([\d,]+\.?\d*)\s*(?:[▾▴]|▴|▾)', div_text)
            if price_match:
                data["price"] = float(price_match.group(1).replace(",", ""))
        
        # Extract change
        div_text = price_div.get_text()
        change_match = re.search(r'([▾▴])\s*([\d,]+\.?\d*)\s*(?:\(([\d,]+\.?\d*)%\))?', div_text)
        if change_match:
            direction = change_match.group(1)
            change_value = float(change_match.group(2).replace(",", ""))
            data["change_abs"] = -change_value if direction == "▾" else change_value
            if change_match.group(3):
                pct_value = float(change_match.group(3).replace(",", ""))
                data["change_pct"] = -pct_value if direction == "▾" else pct_value
    
    # ========================================================================
    # 3. EXTRACT MARKET PERFORMANCE
    # ========================================================================
    
    perf_div = soup.find("div", class_="t", attrs={"data-perf": True})
    if perf_div:
        all_cells = perf_div.find_all("td")
        perf_values = []
        for cell in all_cells:
            text = cell.get_text(strip=True)
            if text and '%' in text:
                perf_values.append(_parse_percentage(text))
        
        if len(perf_values) >= 6:
            data["perf_1wk"] = perf_values[0]
            data["perf_4wk"] = perf_values[1]
            data["perf_3mo"] = perf_values[2]
            data["perf_6mo"] = perf_values[3]
            data["perf_1yr"] = perf_values[4]
            data["perf_ytd"] = perf_values[5]
    
    # ========================================================================
    # 4. EXTRACT COMPANY PROFILE
    # ========================================================================
    
    fact_div = soup.find("div", class_="t", attrs={"data-fact": True})
    if fact_div:
        dds = fact_div.find_all("dd")
        
        if len(dds) >= 1:
            sector_text = dds[0].get_text(strip=True)
            data["sector"] = sector_text if sector_text != "—" else ""
        if len(dds) >= 2:
            industry_text = dds[1].get_text(strip=True)
            data["industry"] = industry_text if industry_text != "—" else ""
        if len(dds) >= 3:
            address_text = dds[2].get_text(strip=True)
            data["address"] = address_text if address_text != "—" else ""
        if len(dds) >= 4:
            telephone_text = dds[3].get_text(strip=True)
            data["telephone"] = telephone_text if telephone_text != "—" else ""
        if len(dds) >= 5:
            email_link = dds[4].find("a")
            if email_link:
                data["email"] = email_link.get_text(strip=True)
            else:
                email_text = dds[4].get_text(strip=True)
                data["email"] = email_text if email_text != "—" else ""
        if len(dds) >= 6:
            website_link = dds[5].find("a")
            if website_link:
                data["website"] = website_link.get_text(strip=True)
            else:
                website_text = dds[5].get_text(strip=True)
                data["website"] = website_text if website_text != "—" else ""
    
    # ========================================================================
    # 5. EXTRACT TEXT-BASED DATA
    # ========================================================================
    
    page_text = soup.get_text()
    
    founded_match = re.search(r"founded on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", page_text, re.IGNORECASE)
    if founded_match:
        data["founded"] = founded_match.group(1)
    
    employees_match = re.search(r"(\d+(?:,\d+)?)\s*employees", page_text, re.IGNORECASE)
    if employees_match:
        data["employees"] = int(employees_match.group(1).replace(",", ""))
    
    rank_match = re.search(r"the\s+(\d+)(?:st|nd|rd|th)\s+most valuable stock", page_text, re.IGNORECASE)
    if rank_match:
        data["value_rank"] = int(rank_match.group(1))
    
    pct_match = re.search(r"makes about\s+([\d.]+)%", page_text, re.IGNORECASE)
    if pct_match:
        data["value_pct"] = float(pct_match.group(1))
    
    traded_match = re.search(r"#(\d+)\s+most traded stock", page_text, re.IGNORECASE)
    if traded_match:
        data["traded_rank"] = int(traded_match.group(1))
    
    prev_match = re.search(r"previous closing price of\s+([\d,]+\.?\d*)", page_text, re.IGNORECASE)
    if prev_match:
        data["prev_close"] = float(prev_match.group(1).replace(",", ""))
    
    year_start_match = re.search(r"began the year with a share price of\s+([\d,]+\.?\d*)", page_text, re.IGNORECASE)
    if year_start_match:
        data["year_start"] = float(year_start_match.group(1).replace(",", ""))
    
    ytd_gain_match = re.search(r"gained\s+([\d,]+\.?\d*)%", page_text, re.IGNORECASE)
    if ytd_gain_match:
        data["ytd_gain"] = float(ytd_gain_match.group(1).replace(",", ""))
    
    return data if data["price"] > 0 else None


def ngx_scrape_stocks(symbols: list) -> Dict[str, Dict[str, Any]]:
    """
    Scrape multiple NGX stocks.
    
    Args:
        symbols: List of stock ticker symbols
    
    Returns:
        Dictionary mapping symbol to stock data dict
    """
    results = {}
    for symbol in symbols:
        result = ngx_scrape_stock(symbol)
        if result:
            results[symbol] = result
        time.sleep(random.uniform(0.5, 1))
    return results
    

def ngx_scrape_market_indices() -> Optional[Dict[str, Any]]:
    """
    Scrape market overview from the main NGX page.
    
    Returns:
        Dictionary with keys: asi_value, asi_change, asi_change_pct, ytd_change, ytd_pct, market_cap, market_cap_value
    """
    resp = _fetch(f"{SCRAPER_BASE_URL}/")
    if not resp:
        return None
    
    soup = BeautifulSoup(resp.text, "html.parser")
    data = {
        "asi_value": 0.0,
        "asi_change": 0.0,
        "asi_change_pct": 0.0,
        "ytd_change": 0.0,
        "ytd_pct": 0.0,
        "market_cap": "",
        "market_cap_value": 0.0,
    }
    
    table = soup.find("table", style=lambda x: x and "margin-top:.125em" in x)
    if not table:
        table = soup.find("table")
    
    if table:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                asi_cell = cells[0].get_text(strip=True)
                asi_match = re.search(r"([\d,]+\.?\d*)\s*\(([+-]?[\d,]+\.?\d*)\)", asi_cell)
                if asi_match:
                    if asi_match.group(1):
                        data["asi_value"] = float(asi_match.group(1).replace(",", ""))
                    if len(asi_match.groups()) > 1 and asi_match.group(2):
                        data["asi_change"] = float(asi_match.group(2).replace(",", ""))
                
                ytd_cell = cells[1].get_text(strip=True)
                ytd_match = re.search(r"([+-]?[\d,]+\.?\d*)\s*\(([+-]?[\d.]+)%\)", ytd_cell)
                if ytd_match:
                    data["ytd_change"] = float(ytd_match.group(1).replace(",", ""))
                    data["ytd_pct"] = float(ytd_match.group(2))
                
                data["market_cap"] = cells[2].get_text(strip=True)
                
                mcap_value = re.search(r"([\d.]+)([TBM])", data["market_cap"], re.IGNORECASE)
                if mcap_value:
                    data["market_cap_value"] = _parse_large_number(mcap_value.group(1) + mcap_value.group(2))
                
                break
    
    asi_pct_div = soup.find("div", class_="h2")
    if asi_pct_div:
        pct_span = asi_pct_div.find("span", class_=["hi", "lo"])
        if pct_span:
            pct_text = pct_span.get_text(strip=True)
            pct_match = re.search(r'\(([+-]?[\d.]+)%\)', pct_text)
            if pct_match:
                data["asi_change_pct"] = float(pct_match.group(1))
    
    return data