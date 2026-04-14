"""SEC EDGAR 13F Filing Parser."""
import httpx
from datetime import date
from xml.etree import ElementTree
from sqlalchemy.orm import Session

from core.config import get_settings
from core.models import HedgeFundFiling, HedgeFundPosition

settings = get_settings()

# Top Hedge Funds mit CIK-Nummern
TOP_FUNDS = {
    "Bridgewater Associates": "0001350694",
    "Citadel Advisors": "0001423053",
    "Renaissance Technologies": "0001037389",
    "Two Sigma Investments": "0001179392",
    "DE Shaw & Co": "0001009207",
    "AQR Capital Management": "0001167557",
    "Man Group": "0001450144",
    "Millennium Management": "0001273087",
    "Point72 Asset Management": "0001603466",
    "Tiger Global Management": "0001167483",
    "Pershing Square Capital": "0001336528",
    "Baupost Group": "0001061768",
    "Viking Global Investors": "0001103804",
    "Elliott Investment Management": "0001048445",
    "Third Point": "0001040273",
    "Lone Pine Capital": "0001061165",
    "Coatue Management": "0001535392",
    "D1 Capital Partners": "0001649339",
    "Dragoneer Investment": "0001571996",
    "Greenlight Capital": "0001079114",
}

EDGAR_BASE = "https://efts.sec.gov/LATEST/search-index?q=%2213F%22&dateRange=custom"
EDGAR_FILINGS = "https://www.sec.gov/cgi-bin/browse-edgar"


def fetch_latest_13f(cik: str, fund_name: str, db: Session) -> HedgeFundFiling | None:
    """Neuestes 13F Filing für einen Fund abrufen."""
    headers = {
        "User-Agent": settings.sec_edgar_user_agent or "TradingIntelligence research@tradingintel.app",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json",
    }

    submissions_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    resp = httpx.get(submissions_url, headers=headers, timeout=30)

    if resp.status_code != 200:
        return None

    data = resp.json()
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])

    for i, form in enumerate(forms):
        if form == "13F-HR" and i < len(accessions):
            accession = accessions[i]
            filing_date_str = dates[i]

            existing = db.query(HedgeFundFiling).filter(
                HedgeFundFiling.accession_number == accession
            ).first()
            if existing:
                return existing

            filing = HedgeFundFiling(
                fund_name=fund_name,
                cik=cik,
                filing_date=date.fromisoformat(filing_date_str),
                accession_number=accession,
            )
            db.add(filing)
            db.flush()

            # Positionen aus der XML-Tabelle laden
            parse_13f_positions(cik, accession, filing, headers, db)

            db.commit()
            return filing

    return None


# CUSIP → Ticker Mapping (Top Holdings, wird on-the-fly erweitert)
CUSIP_TO_TICKER = {
    "037833100": "AAPL", "594918104": "MSFT", "67066G104": "NVDA",
    "02079K305": "GOOGL", "02079K107": "GOOG", "023135106": "AMZN",
    "30303M102": "META", "88160R101": "TSLA", "11135F101": "AVGO",
    "46625H100": "JPM", "92826C839": "V", "478160104": "JNJ",
    "91324P102": "UNH", "931142103": "WMT", "742718109": "PG",
    "437076102": "HD", "191216100": "KO", "713448108": "PEP",
    "58933Y105": "MRK", "00287Y109": "ABBV", "529771107": "LLY",
    "22160K105": "COST", "79466L302": "CRM", "64110L106": "NFLX",
    "007903107": "AMD", "458140100": "INTC",
}


def parse_13f_positions(
    cik: str, accession: str, filing: HedgeFundFiling, headers: dict, db: Session
):
    """Parse 13F XML Informationstabelle."""
    acc_clean = accession.replace("-", "")

    # Erst Index-Seite laden um die XML-Datei zu finden
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_clean}/"
    try:
        index_resp = httpx.get(index_url, headers=headers, timeout=30)
        if index_resp.status_code != 200:
            return

        import re
        xml_matches = re.findall(r'href="([^"]*infotable[^"]*\.xml)"', index_resp.text, re.IGNORECASE)
        if not xml_matches:
            xml_matches = ["infotable.xml"]

        xml_path = xml_matches[0]
        if xml_path.startswith("/"):
            xml_url = f"https://www.sec.gov{xml_path}"
        else:
            xml_url = f"{index_url}{xml_path}"

        resp = httpx.get(xml_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return

        root = ElementTree.fromstring(resp.content)

        # Namespace dynamisch erkennen
        ns_match = re.match(r'\{(.+?)\}', root.tag)
        ns_uri = ns_match.group(1) if ns_match else "http://www.sec.gov/edgar/document/thirteenf/informationtable"
        ns = {"ns": ns_uri}

        count = 0
        for entry in root.findall(".//ns:infoTable", ns):
            name = entry.findtext("ns:nameOfIssuer", "", ns).strip()
            cusip = entry.findtext("ns:cusip", "", ns).strip()
            value_text = entry.findtext("ns:value", "0", ns).strip()
            shares_el = entry.find("ns:shrsOrPrnAmt/ns:sshPrnamt", ns)
            shares = shares_el.text.strip() if shares_el is not None and shares_el.text else "0"

            # CUSIP → Ticker Lookup
            ticker_symbol = CUSIP_TO_TICKER.get(cusip)

            position = HedgeFundPosition(
                filing_id=filing.id,
                symbol=ticker_symbol,
                company_name=name,
                cusip=cusip,
                value=int(value_text) if value_text else 0,
                shares=int(shares) if shares else 0,
                change_type="UNKNOWN",
            )
            db.add(position)
            count += 1

        return count

    except Exception:
        return 0


def scan_all_funds(db: Session):
    """Scanne alle Top-Funds auf neue 13F-Filings."""
    for fund_name, cik in TOP_FUNDS.items():
        try:
            fetch_latest_13f(cik, fund_name, db)
        except Exception:
            continue
