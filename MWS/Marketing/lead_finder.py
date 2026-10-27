"""Maier Lead Finder — discover AND rank leads in one script.

Install: py -m pip install overturemaps google-api-python-client google-auth-httplib2 google-auth-oauthlib ddgs
Run:     py lead_finder.py --city prairieville --category cleaning --radius 5000 --top 50 --require-email
Rank saved CSVs without downloading: py lead_finder.py --rank-only --top 50 --require-email

No paid API keys. Google review opens links for human review; Gmail sends only after explicit confirmation.
"""
import argparse
import base64
from email.message import EmailMessage
from email.utils import getaddresses
import csv
import json
import html
import webbrowser
import math
import os
import time
import re
import shutil
import subprocess
import sys
import sysconfig
import sqlite3
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse
import urllib.request
import urllib.error
from difflib import SequenceMatcher
from pathlib import Path


CITIES = {
    "prairieville": (30.3027, -90.9701),
    "gonzales": (30.2385, -90.9201),
    "batonrouge": (30.4515, -91.1871),
    "walker": (30.4879, -90.8615),
}
KEYWORDS = {
    "cleaning": ("clean", "janitor", "maid", "housekeep", "carpet", "window_wash"),
    "landscaping": ("landscap", "lawn", "garden", "tree_service", "yard"),
    "detailing": ("detail", "car_wash", "auto_clean"),
    "pressurewashing": ("pressure_wash", "power_wash", "exterior_clean"),
    "handyman": ("handyman", "handyperson", "home_repair", "property_maintenance"),
}
FIELDS = ["name", "category", "city", "address", "phone", "email", "social", "website_status", "confidence", "source_id", "latitude", "longitude", "maps_link"]


def first(value):
    if isinstance(value, list):
        return str(value[0]) if value else ""
    if isinstance(value, str):
        return value
    return ""


def get_cli():
    found = shutil.which("overturemaps")
    if found:
        return found
    scripts = Path(sysconfig.get_path("scripts"))
    candidate = scripts / ("overturemaps.exe" if sys.platform == "win32" else "overturemaps")
    return str(candidate) if candidate.exists() else None


def distance_m(lat1, lon1, lat2, lon2):
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat = r2 - r1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2)**2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def iter_features(path):
    with path.open("r", encoding="utf-8") as f:
        initial = f.read(150)
        f.seek(0)
        if initial.lstrip().startswith('{'):
            data = json.load(f)
            if data.get("type") == "FeatureCollection":
                yield from data.get("features", [])
            elif data.get("type") == "Feature":
                yield data
        else:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def finder_main(argv=None):
    parser = argparse.ArgumentParser(description="Find potential local business leads with no website listed in Overture Maps")
    parser.add_argument("--city", choices=CITIES, default="prairieville")
    parser.add_argument("--category", choices=["all", *KEYWORDS], default="all")
    parser.add_argument("--radius", type=int, default=5000, help="Search radius in meters (maximum 15000)")
    parser.add_argument("--refresh", action="store_true", help="Download data again instead of using local cache")
    args = parser.parse_args(argv)
    if not 250 <= args.radius <= 15000:
        parser.error("--radius must be between 250 and 15000 meters")

    lat, lon = CITIES[args.city]
    lat_delta = args.radius / 111320
    lon_delta = args.radius / (111320 * math.cos(math.radians(lat)))
    bbox = f"{lon-lon_delta:.6f},{lat-lat_delta:.6f},{lon+lon_delta:.6f},{lat+lat_delta:.6f}"
    cache_dir = Path(".lead_cache")
    cache_dir.mkdir(exist_ok=True)
    source = cache_dir / f"overture_{args.city}_{args.radius}.geojson"
    print(f"Searching {args.category} near {args.city} ({args.radius/1000:g} km)...")
    if args.refresh or not source.exists():
        cli = get_cli()
        if not cli:
            print("Missing Overture CLI. Install with: py -m pip install overturemaps")
            sys.exit(1)
        print("Downloading free Overture Maps places data for this area...")
        command = [cli, "download", "--bbox", bbox, "-f", "geojson", "--type", "place", "-o", str(source)]
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            source.unlink(missing_ok=True)
            print(f"Download failed: {e}")
            print("This is a remote-data download problem; try again later or use a smaller radius.")
            sys.exit(1)
    else:
        print("Using locally cached place data.")

    leads = []
    count = 0
    matched = 0
    seen = set()
    for feature in iter_features(source):
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        longitude, latitude = coords[:2]
        if distance_m(lat, lon, latitude, longitude) > args.radius:
            continue
        count += 1
        names = props.get("names") or {}
        name = names.get("primary") if isinstance(names, dict) else ""
        if not name:
            continue
        taxonomy = props.get("taxonomy") or {}
        cats = [str(props.get("basic_category") or "")]
        if isinstance(taxonomy, dict):
            cats.extend([str(taxonomy.get("primary") or ""), *(taxonomy.get("hierarchy") or []), *(taxonomy.get("alternates") or [])])
        # Legacy data compatibility
        old = props.get("categories") or {}
        if isinstance(old, dict):
            cats.append(str(old.get("primary") or ""))
        category_text = " ".join(cats).lower()
        if args.category != "all" and not any(k in category_text for k in KEYWORDS[args.category]):
            continue
        matched += 1
        if first(props.get("websites")):
            continue
        key = (name.strip().lower(), round(latitude, 4), round(longitude, 4))
        if key in seen:
            continue
        seen.add(key)
        addresses = props.get("addresses") or []
        address = addresses[0] if addresses and isinstance(addresses[0], dict) else {}
        row = {
            "name": name,
            "category": cats[1] if len(cats) > 1 else cats[0],
            "city": address.get("locality") or args.city,
            "address": address.get("freeform") or "",
            "phone": first(props.get("phones")),
            "email": first(props.get("emails")),
            "social": first(props.get("socials")),
            "website_status": "NOT LISTED — VERIFY MANUALLY",
            "confidence": props.get("confidence", ""),
            "source_id": props.get("id") or feature.get("id") or "",
            "latitude": latitude,
            "longitude": longitude,
            "maps_link": f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=17/{latitude}/{longitude}",
        }
        leads.append(row)

    leads.sort(key=lambda x: (not bool(x["email"]), not bool(x["phone"]), x["name"].lower()))
    output = Path(f"leads_{args.city}_{args.category}.csv")
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(leads)
    print(f"Places in radius: {count}")
    print(f"Matching category: {matched}")
    print(f"Potential leads with no website listed: {len(leads)}")
    print(f"Saved: {output.resolve()}")
    print("Reminder: 'not listed' does not mean the business has no website. Verify each lead before outreach.")




PRIORITY_CATEGORIES = {
    'home_cleaning': 36, 'cleaning_service': 36, 'janitorial_service': 36,
    'landscaping': 36, 'lawn_care': 36, 'lawn_and_garden_service': 36,
    'pressure_washing': 36, 'power_washing': 36, 'window_cleaning': 33,
    'auto_detailing': 35, 'car_detailing': 35, 'mobile_detailing': 35,
    'handyman': 35, 'handyman_service': 35,
    'painting': 29, 'painting_service': 29, 'house_painting': 29,
    'roofing': 27, 'roofing_contractor': 27,
    'contractor': 23,
    'building_or_construction_service': 23,
    'flooring': 25, 'fencing': 25, 'plumbing': 24, 'electrician': 24,
    'hvac': 24, 'pest_control': 24, 'pool_cleaning': 33,
    'car_wash': 19, 'automotive_repair': 15,
    'photographer': 22, 'photography': 22,
    'bakery': 18, 'barber': 16, 'hair_salon': 15, 'beauty_salon': 14,
    'nail_salon': 14, 'pet_grooming': 23, 'party_and_event_planning': 22,
}

# Additional matches for varying Overture category labels.
KEYWORD_SCORES = {
    'clean': 35, 'maid': 35, 'janitor': 35, 'landscap': 35,
    'lawn': 35, 'pressure_wash': 35, 'power_wash': 35,
    'detail': 34, 'handyman': 35, 'soft_wash': 35,
    'painting': 28, 'roof': 26, 'contractor': 22,
    'pool_service': 31, 'tree_service': 29, 'fence': 25,
    'window_wash': 30, 'gutter': 30,
}

EXCLUDED_CATEGORY_TERMS = (
    'government', 'military', 'police', 'fire_station', 'hospital',
    'health_care', 'school', 'university', 'religious', 'place_of_worship',
    'park', 'cemetery', 'gas_station', 'atm', 'bank', 'post_office',
    'public_transport', 'bus_stop', 'library', 'courthouse',
    'dry_cleaning', 'home_improvement_store', 'childcare', 'daycare', 'preschool', 'nursery',
)

CHAIN_NAMES = (
    'walmart', 'mcdonald', 'starbucks', 'subway', 'taco bell',
    'burger king', 'wendy', 'dollar general', 'dollar tree',
    'walgreens', 'cvs pharmacy', 'chick-fil-a', 'domino',
    'popeyes', 'autozone', 'o\'reilly auto', 'home depot', 'lowe\'s',
)

OUTPUT_COLUMNS = [
    'rank', 'lead_score', 'name', 'category', 'city', 'address', 'email',
    'phone', 'social', 'website_status', 'verification_status',
    'reason', 'source_id', 'maps_link', 'latitude', 'longitude',
    'source_files', 'search_link', 'activity_search_link', 'contact_status', 'notes', 'last_contacted',
    'activity_status', 'activity_checked_at', 'website_url', 'website_check', 'website_checked_at', 'verification_checked_at',
]


def normalize_name(value):
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')
    return digits[-10:] if len(digits) >= 10 else ''


def normalize_email(value):
    value = (value or '').strip().lower()
    return value if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) else ''


def category_score(category, name):
    category = (category or '').strip().casefold().replace(' ', '_')
    name = (name or '').strip().casefold().replace(' ', '_')
    if any(term in category for term in EXCLUDED_CATEGORY_TERMS):
        return 0
    if category in PRIORITY_CATEGORIES:
        return PRIORITY_CATEGORIES[category]
    matches = [score for keyword, score in KEYWORD_SCORES.items()
               if keyword in category or (category in ('', 'business', 'service', 'home_service') and keyword in name)]
    return max(matches, default=0)


def score_record(record):
    name = (record.get('name') or '').strip()
    category = (record.get('category') or '').strip()
    if not name or any(chain in name.casefold() for chain in CHAIN_NAMES):
        return None
    industry = category_score(category, name)
    if industry == 0:
        return None
    email = normalize_email(record.get('email'))
    phone = normalize_phone(record.get('phone'))
    social = (record.get('social') or '').strip()
    website_status = (record.get('website_status') or '').strip()
    if website_status and not any(word in website_status.casefold() for word in ('not listed', 'missing', 'unknown', 'verify')):
        return None
    score = industry + (30 if email else 0) + (12 if phone else 0) + (10 if social else 0)
    score += 5 if (record.get('address') or '').strip() else 0
    score += 3 if (record.get('city') or '').strip() else 0
    score = min(100, score)
    reason = [f'industry fit ({industry})']
    if email: reason.append('public email listed')
    if phone: reason.append('phone listed')
    if social: reason.append('social profile listed')
    if not email: reason.append('email missing')
    result = dict(record)
    result.update(lead_score=score, email=email, reason='; '.join(reason),
                  verification_status='NOT VERIFIED', rank='', source_files='')
    return result


def merge_records(existing, incoming):
    # Keep the more complete record, filling gaps from the other.
    if incoming['lead_score'] > existing['lead_score']:
        existing, incoming = incoming, existing
    for key in ('email', 'phone', 'social', 'address', 'maps_link', 'latitude', 'longitude', 'source_id', 'city'):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]
    existing['source_files'] = '; '.join(sorted(set(
        filter(None, (existing.get('source_files', '') + ';' + incoming.get('source_files', '')).split(';'))
    )))
    rescored = score_record(existing)
    if rescored:
        existing['lead_score'] = rescored['lead_score']
        existing['reason'] = rescored['reason']
    return existing


def database(path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS lead_tracking (
        lead_key TEXT PRIMARY KEY, verification_status TEXT NOT NULL DEFAULT 'not_checked',
        contact_status TEXT NOT NULL DEFAULT 'not_contacted',
        notes TEXT NOT NULL DEFAULT '', last_contacted TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT ''
    )""")
    # Add columns without discarding an existing tracking database.
    existing = {row[1] for row in conn.execute('PRAGMA table_info(lead_tracking)')}
    for column in ('activity_status', 'activity_checked_at', 'website_url', 'website_check', 'website_checked_at', 'verification_checked_at'):
        if column not in existing:
            conn.execute(f'ALTER TABLE lead_tracking ADD COLUMN {column} TEXT NOT NULL DEFAULT \'\'')
    conn.execute('''CREATE TABLE IF NOT EXISTS gmail_drafts (
        lead_key TEXT PRIMARY KEY,
        recipient TEXT NOT NULL,
        gmail_draft_id TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    conn.execute("""CREATE TABLE IF NOT EXISTS sent_emails (
        gmail_message_id TEXT PRIMARY KEY,
        lead_key TEXT NOT NULL,
        recipient TEXT NOT NULL,
        business_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )""")
    conn.execute('CREATE INDEX IF NOT EXISTS sent_emails_recipient ON sent_emails(recipient)')
    conn.commit()
    return conn


def lead_key(record):
    sid = (record.get('source_id') or '').strip()
    if sid:
        return 'id:' + sid
    return 'name:' + normalize_name(record.get('name')) + ':' + normalize_name(record.get('city'))


def enrich_tracking(conn, record):
    key = lead_key(record)
    conn.execute('INSERT OR IGNORE INTO lead_tracking (lead_key) VALUES (?)', (key,))
    state = conn.execute('''SELECT verification_status, contact_status, notes, last_contacted,
          activity_status, activity_checked_at, website_url, website_check,
          website_checked_at, verification_checked_at FROM lead_tracking WHERE lead_key=?''', (key,)).fetchone()
    for field, value in zip(('verification_status', 'contact_status', 'notes', 'last_contacted',
                             'activity_status', 'activity_checked_at', 'website_url',
                             'website_check', 'website_checked_at', 'verification_checked_at'), state):
        record[field] = value
    if not record['activity_status']:
        record['activity_status'] = 'unknown'
    query = f"{record.get('name','')} {record.get('city','')} Louisiana official website"
    record['search_link'] = 'https://www.google.com/search?q=' + quote_plus(query)
    activity_query = f"{record.get('name','')} {record.get('city','')} Louisiana business reviews recent posts"
    record['activity_search_link'] = 'https://www.google.com/search?q=' + quote_plus(activity_query)
    return record


def update_tracking(conn, key, field, value):
    allowed = {'verification_status', 'contact_status', 'notes', 'activity_status', 'website_url', 'website_check'}
    if field not in allowed:
        raise ValueError('Invalid tracking field')
    conn.execute('INSERT OR IGNORE INTO lead_tracking (lead_key) VALUES (?)', (key,))
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    if field == 'contact_status' and value == 'contacted':
        conn.execute(f'UPDATE lead_tracking SET {field}=?, last_contacted=?, updated_at=? WHERE lead_key=?', (value, now, now, key))
    elif field == 'verification_status':
        conn.execute('UPDATE lead_tracking SET verification_status=?, verification_checked_at=?, updated_at=? WHERE lead_key=?',
                     (value, now, now, key))
    elif field == 'activity_status':
        conn.execute('UPDATE lead_tracking SET activity_status=?, activity_checked_at=?, updated_at=? WHERE lead_key=?',
                     (value, now, now, key))
    elif field == 'website_check':
        conn.execute('UPDATE lead_tracking SET website_check=?, website_checked_at=?, updated_at=? WHERE lead_key=?',
                     (value, now, now, key))
    else:
        conn.execute(f'UPDATE lead_tracking SET {field}=?, updated_at=? WHERE lead_key=?', (value, now, key))
    conn.commit()


def check_known_website(url):
    """Check connectivity of a KNOWN website, not whether a business owns a website."""
    if not url:
        return 'no_url_provided'
    if not urlparse(url).scheme:
        url = 'https://' + url
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return 'invalid_url'
    # Don't follow redirects to internal network addresses from user-provided URLs.
    import ipaddress
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if not ip.is_global:
            return 'invalid_url'
    except ValueError:
        if parsed.hostname in ('localhost',) or parsed.hostname.endswith(('.local', '.internal')):
            return 'invalid_url'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MaierLeadFinder/1.0 (manual business website check)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            code = response.status
            return f'http_{code}_responding' if 200 <= code < 400 else f'http_{code}_review'
    except urllib.error.HTTPError as exc:
        return f'http_{exc.code}_review'
    except Exception as exc:
        return f'unreachable_{type(exc).__name__}'


def manage_record(folder, number, verify=None, contact=None, notes=None, activity=None,
                  website_url=None, check_website=False):
    path = folder / 'top_leads.csv'
    if not path.exists():
        raise SystemExit('top_leads.csv is missing. Run a search or --rank-only first.')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        records = list(csv.DictReader(handle))
    if number < 1 or number > len(records):
        raise SystemExit(f'--lead must be between 1 and {len(records)}')
    record = records[number - 1]
    key = lead_key(record)
    conn = database(folder / 'lead_tracking.sqlite3')
    if verify is not None:
        update_tracking(conn, key, 'verification_status', verify)
    if contact is not None:
        update_tracking(conn, key, 'contact_status', contact)
    if notes is not None:
        update_tracking(conn, key, 'notes', notes)
    if activity is not None:
        update_tracking(conn, key, 'activity_status', activity)
    if website_url is not None:
        update_tracking(conn, key, 'website_url', website_url)
    if check_website:
        enrich_tracking(conn, record)
        result = check_known_website(record.get('website_url', ''))
        update_tracking(conn, key, 'website_check', result)
    enrich_tracking(conn, record)
    conn.commit()
    print(f"Lead #{number}: {record['name']} ({record['city']})")
    print(f"Website verification: {record['verification_status']}")
    print(f"Contact status: {record['contact_status']}")
    print(f"Email: {record.get('email','')}")
    print(f"Website verification: {record['verification_status']}")
    print(f"Activity: {record['activity_status']}")
    print(f"Known website: {record.get('website_url','') or 'none recorded'}")
    print(f"Website response: {record.get('website_check','') or 'not checked'}")
    print(f"Search website: {record['search_link']}")
    print(f"Search activity: {record['activity_search_link']}")
    if record['notes']:
        print(f"Notes: {record['notes']}")
    print('Tracking saved to lead_tracking.sqlite3. Run --rank-only to refresh top_leads.csv.')
    conn.close()


def email_content(record):
    """Simple, consistent outreach template with a name/business greeting."""
    business = (record.get('name') or '').strip()
    contact_name = (record.get('contact_name') or '').strip()
    greeting = contact_name or business
    salutation = f"Hello {greeting}," if greeting else "Hello,"
    subject = f"Website services for {business}" if business else "Website design for your business"
    body = (f"{salutation}\n\n"
            "I hope you're doing well!\n\n"
            "My name is Michael Maier, and I run Maier Web Solutions, a small website "
            "design business based in the Prairieville area.\n\n"
            "I help local businesses create affordable, professional websites that make "
            "it easier for customers to find them online, learn about their services, "
            "and get in touch.\n\n"
            "I wanted to reach out and see if you'd be interested in having a website "
            "built for your business.\n\n"
            "You can see examples of my work at https://maierwebsolutions.com. "
            "If you're interested or have any questions, feel free to reply!\n\n"
            "If you'd rather not hear from me again, just let me know.\n\n"
            "Best regards,\n"
            "Michael Maier\n"
            "Maier Web Solutions\n"
            "https://maierwebsolutions.com\n"
            "PO Box 434\n"
            "Prairieville, LA 70769")
    return subject, body


def eligible_for_draft(record):
    return (record.get('verification_status') == 'no_website_found'
            and record.get('activity_status') == 'likely_active'
            and record.get('contact_status') == 'not_contacted'
            and bool(normalize_email(record.get('email'))))


def write_drafts(folder, records):
    drafts = folder / 'email_drafts.csv'
    columns = ['name', 'email', 'subject', 'body', 'verification_status', 'contact_status']
    with drafts.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            if not eligible_for_draft(record):
                continue
            subject, body = email_content(record)
            writer.writerow({'name': record['name'], 'email': record['email'],
                             'subject': subject, 'body': body,
                             'verification_status': record['verification_status'],
                             'contact_status': record['contact_status']})
    print(f'Draft-only CSV saved: {drafts.resolve()} (nothing sent)')


def gmail_service(folder):
    """Authorize this desktop app for Gmail sending and Sent history."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise SystemExit('Missing Gmail libraries. Run: py -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib') from exc

    scope = ['https://www.googleapis.com/auth/gmail.send',
             'https://www.googleapis.com/auth/gmail.readonly']
    credentials_path = folder / 'credentials.json'
    token_path = folder / 'token.json'
    if not credentials_path.is_file():
        raise SystemExit(f'Missing {credentials_path}. Download the Desktop OAuth client JSON and rename it credentials.json.')
    creds = None
    if token_path.exists():
        try:
            saved_scopes = set(json.loads(token_path.read_text(encoding='utf-8')).get('scopes', []))
            if not set(scope).issubset(saved_scopes):
                print('Gmail Sent access needs a new Google authorization.')
            else:
                creds = Credentials.from_authorized_user_file(str(token_path), scope)
        except (ValueError, OSError):
            raise SystemExit('token.json is invalid. Rename or delete it, then retry authorization.')
    if creds and not creds.has_scopes(scope):
        print('Additional read-only Sent Mail permission needed; reauthorizing.')
        creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                print('Saved authorization expired or was revoked; opening sign-in again.')
                creds = None
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scope)
            creds = flow.run_local_server(port=0, open_browser=True)
        token_path.write_text(creds.to_json(), encoding='utf-8')
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def all_lead_records(folder):
    """Read known leads from all generated CSVs (not just today's top 50)."""
    records = {}
    for path in sorted(folder.glob('leads_*.csv')) + [folder / 'top_leads.csv']:
        if not path.exists():
            continue
        with path.open(newline='', encoding='utf-8-sig') as handle:
            for record in csv.DictReader(handle):
                email = normalize_email(record.get('email'))
                if email:
                    records.setdefault(email, record)
    return records


def sent_to(conn, record):
    email = normalize_email(record.get('email'))
    key = lead_key(record)
    return bool(conn.execute('SELECT 1 FROM sent_emails WHERE recipient=? OR lead_key=? LIMIT 1',
                             (email, key)).fetchone())


def sync_sent(folder, service=None, quiet=False):
    """Read Gmail Sent folder; store matches to local business emails. No sends."""
    known = all_lead_records(folder)
    conn = database(folder / 'lead_tracking.sqlite3')
    if not known:
        conn.close()
        raise SystemExit('No lead CSVs found with emails. Generate leads first.')
    if service is None:
        service = gmail_service(folder)
    added = 0
    scanned = 0
    page = None
    try:
        while True:
            args = {'userId': 'me', 'labelIds': ['SENT'], 'maxResults': 500}
            if page:
                args['pageToken'] = page
            response = service.users().messages().list(**args).execute()
            for item in response.get('messages', []):
                scanned += 1
                mid = item['id']
                if conn.execute('SELECT 1 FROM sent_emails WHERE gmail_message_id=?', (mid,)).fetchone():
                    continue
                msg = service.users().messages().get(userId='me', id=mid,
                          format='metadata', metadataHeaders=['To', 'Subject', 'Date']).execute()
                headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
                recipients = {normalize_email(email) for _, email in getaddresses([headers.get('to', '')])}
                matched = recipients.intersection(known)
                for email in matched:
                    record = known[email]
                    key = lead_key(record)
                    when = datetime.fromtimestamp(int(msg.get('internalDate', 0))/1000, timezone.utc).isoformat()
                    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
                    conn.execute('INSERT OR IGNORE INTO sent_emails VALUES (?,?,?,?,?,?,?)',
                                 (mid, key, email, record.get('name',''), headers.get('subject',''), when, now))
                    update_tracking(conn, key, 'contact_status', 'contacted')
                    added += 1
            page = response.get('nextPageToken')
            if not page:
                break
        conn.commit()
        if not quiet:
            print(f'Gmail Sent sync complete: scanned {scanned} messages; recorded {added} new lead emails.')
            print('History saved in lead_tracking.sqlite3; nothing was sent.')
    finally:
        conn.close()
    return added


def sent_report(folder):
    conn = database(folder / 'lead_tracking.sqlite3')
    try:
        rows = conn.execute('SELECT business_name,recipient,subject,sent_at FROM sent_emails ORDER BY sent_at DESC').fetchall()
        print(f'Sent email history: {len(rows)} recorded messages')
        for name, email, subject, when in rows[:100]:
            print(f'{when} | {name} | {email} | {subject}')
    finally:
        conn.close()


def send_gmail_email(folder, number):
    """Send exactly one verified lead email, and log Gmail's message ID in SQLite."""
    path = folder / 'top_leads.csv'
    if not path.exists():
        raise SystemExit('top_leads.csv is missing. Run --rank-only first.')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        records = list(csv.DictReader(handle))
    if not 1 <= number <= len(records):
        raise SystemExit(f'--gmail-send must be between 1 and {len(records)}')
    record = records[number - 1]
    conn = database(folder / 'lead_tracking.sqlite3')
    try:
        enrich_tracking(conn, record)
        conn.commit()
        if not eligible_for_draft(record):
            raise SystemExit('Lead not eligible: first verify no_website_found and likely_active; '
                             'it also needs a public email and not_contacted status.')
        key = lead_key(record)
        if sent_to(conn, record):
            print('Already recorded as emailed in SQLite. Nothing sent.')
            return
        subject, body = email_content(record)
        recipient = normalize_email(record['email'])
        print(f'Business: {record["name"]} ({record.get("city", "")})')
        print(f'To: {recipient}\nSubject: {subject}\n')
        print(body)
        print('\nThis will SEND an actual email, not create a draft.')
        confirmation = input(f'Type SEND {number} to email this business: ').strip()
        if confirmation != f'SEND {number}':
            print('Cancelled. Nothing sent.')
            return
        service = gmail_service(folder)
        # Check actual Gmail Sent folder before sending, even if SQLite is out of date.
        sync_sent(folder, service=service, quiet=True)
        if sent_to(conn, record):
            print('Already emailed according to Gmail Sent history. Nothing sent.')
            return
        message = EmailMessage()
        message['To'] = recipient
        message['Subject'] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
        try:
            result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
        except Exception as exc:
            raise SystemExit('Gmail returned an error. Check Gmail Sent before retrying; '
                             f'delivery may be uncertain. Details: {exc}') from exc
        mid = result.get('id')
        if not mid:
            raise SystemExit('Gmail did not return a message ID. Check Sent before retrying.')
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        conn.execute('INSERT OR IGNORE INTO sent_emails '
                     '(gmail_message_id, lead_key, recipient, business_name, subject, sent_at, recorded_at) '
                     'VALUES (?,?,?,?,?,?,?)',
                     (mid, key, recipient, record.get('name', ''), subject, now, now))
        update_tracking(conn, key, 'contact_status', 'contacted')
        conn.commit()
        print(f'SENT to {recipient}. Gmail ID: {mid}')
        print('Recorded in lead_tracking.sqlite3. Run --rank-only to refresh your shortlist.')
    finally:
        conn.close()


def bulk_send(folder, limit, preview=False, quick=False):
    """Send a bounded batch with a single recipient-list confirmation."""
    if not 1 <= limit <= 20:
        raise SystemExit('--bulk-send must be between 1 and 20. Start with 5.')
    path = folder / 'top_leads.csv'
    if not path.exists():
        raise SystemExit('top_leads.csv missing; run --rank-only first.')
    with path.open(newline='', encoding='utf-8-sig') as handle:
        records = list(csv.DictReader(handle))
    conn = database(folder / 'lead_tracking.sqlite3')
    try:
        for record in records:
            enrich_tracking(conn, record)
        conn.commit()
        if not preview:
            print('Checking Gmail Sent history before preparing the batch...')
            service = gmail_service(folder)
            sync_sent(folder, service=service, quiet=False)
        else:
            service = None
        candidates = []
        seen_recipients = set()
        for record in records:
            email = normalize_email(record.get('email'))
            eligible = (record.get('contact_status') == 'not_contacted'
                        and record.get('verification_status') != 'has_website'
                        and record.get('activity_status') != 'inactive'
                        and bool(email)) if quick else eligible_for_draft(record)
            if (eligible and not sent_to(conn, record)
                    and email not in seen_recipients):
                candidates.append(record)
                seen_recipients.add(email)
            if len(candidates) >= limit:
                break
        if not candidates:
            print('No eligible unsent leads. Refresh with --rank-only --top 50 --require-email; nothing sent.' if quick else 'No eligible unsent leads. Manually verify more businesses first; nothing sent.')
            return
        print(f'\nEligible batch: {len(candidates)} of requested {limit}')
        for idx, record in enumerate(candidates, 1):
            print(f' {idx}. {record["name"]} | {record["email"]} | {record.get("city", "")}')
        print('\nMessage example for the first recipient:')
        subject, body = email_content(candidates[0])
        print(f'Subject: {subject}\n\n{body}\n')
        if preview:
            print('PREVIEW ONLY: no emails sent.')
            return
        if quick:
            print('\nQUICK MODE: These businesses have NOT been individually verified. Some may already have websites.')
            print('Review the entire recipient list above. No claim about missing websites will be made.')
        print('This will SEND real emails to every business listed above.')
        approval = input(f'Type SEND {len(candidates)} to confirm this batch: ').strip()
        if approval != f'SEND {len(candidates)}':
            print('Cancelled; nothing sent.')
            return
        sent_count = 0
        for record in candidates:
            if sent_to(conn, record):
                print(f'SKIP already sent: {record["name"]}')
                continue
            recipient = normalize_email(record['email'])
            subject, body = email_content(record)
            message = EmailMessage()
            message['To'] = recipient
            message['Subject'] = subject
            message.set_content(body)
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
            try:
                result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
            except Exception as exc:
                print(f'STOPPED on {recipient}: {exc}')
                print('Check Gmail Sent and run --sync-sent before retrying. Delivery may be uncertain.')
                break
            mid = result.get('id')
            if not mid:
                print('STOPPED: Gmail returned no message ID. Check Gmail Sent before retrying.')
                break
            now = datetime.now(timezone.utc).isoformat(timespec='seconds')
            conn.execute('INSERT OR IGNORE INTO sent_emails '
                         '(gmail_message_id, lead_key, recipient, business_name, subject, sent_at, recorded_at) '
                         'VALUES (?,?,?,?,?,?,?)',
                         (mid, lead_key(record), recipient, record.get('name', ''), subject, now, now))
            update_tracking(conn, lead_key(record), 'contact_status', 'contacted')
            conn.commit()
            sent_count += 1
            print(f'SENT {sent_count}/{len(candidates)}: {record["name"]} <{recipient}>')
            if sent_count < len(candidates):
                time.sleep(10)
        print(f'Finished: {sent_count} emails sent and recorded in SQLite.')
        print('Run --rank-only to update your shortlist.')
    finally:
        conn.close()


def ranker_main(argv=None):
    parser = argparse.ArgumentParser(description='Rank Overture leads without paid APIs.')
    parser.add_argument('--folder', type=Path, default=Path('.'), help='Folder with leads_*.csv files')
    parser.add_argument('--top', type=int, default=50, help='Number of ranked leads to export (default: 50)')
    parser.add_argument('--require-email', action='store_true', help='Include only leads with a public email')
    parser.add_argument('--output', default='top_leads.csv', help='Output CSV filename')
    parser.add_argument('--drafts', action='store_true', help='Generate draft emails for manually verified website-free leads')
    args = parser.parse_args(argv)
    if args.top < 1:
        parser.error('--top must be at least 1')
    files = sorted(args.folder.glob('leads_*.csv'))
    if not files:
        parser.error(f'No leads_*.csv files found in {args.folder.resolve()}')

    raw = []
    for path in files:
        try:
            with path.open('r', newline='', encoding='utf-8-sig') as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or not {'name', 'category'}.issubset(reader.fieldnames):
                    print(f'Skipping {path.name}: missing name/category columns')
                    continue
                for record in reader:
                    record['source_files'] = path.name
                    raw.append(record)
        except (OSError, UnicodeError, csv.Error) as exc:
            print(f'Skipping {path.name}: {exc}')

    candidates = [candidate for record in raw if (candidate := score_record(record))]
    # Deduplicate by source ID, then phone/email, then normalized name and city.
    deduped = {}
    source_to_key = {}
    for record in candidates:
        name = normalize_name(record.get('name'))
        city = normalize_name(record.get('city'))
        sid = (record.get('source_id') or '').strip()
        phone = normalize_phone(record.get('phone'))
        email = normalize_email(record.get('email'))
        # Name plus contact/location protects against merging unrelated businesses sharing a phone.
        keys = [f'id:{sid}'] if sid else []
        if phone: keys.append(f'namephone:{name}:{phone}')
        if email: keys.append(f'nameemail:{name}:{email}')
        keys.append(f'namecity:{name}:{city}')
        found = next((source_to_key[key] for key in keys if key in source_to_key), None)
        if found is None:
            found = len(deduped)
            deduped[found] = record
        else:
            deduped[found] = merge_records(deduped[found], record)
        for key in keys:
            source_to_key[key] = found

    ranked = list(deduped.values())
    if args.require_email:
        ranked = [r for r in ranked if r.get('email')]
    ranked.sort(key=lambda r: (-r['lead_score'], -bool(r.get('email')),
                               r.get('name', '').casefold()))
    conn = database(args.folder / 'lead_tracking.sqlite3')
    for record in ranked:
        enrich_tracking(conn, record)
    conn.commit()
    # Never put opted-out or already-contacted leads into a new outreach shortlist.
    ranked = [r for r in ranked if not sent_to(conn, r) and r['contact_status'] == 'not_contacted'
              and r['verification_status'] != 'has_website'
              and r['activity_status'] != 'inactive']
    selected = ranked[:args.top]
    for index, record in enumerate(selected, start=1):
        record['rank'] = index
    output = args.folder / args.output
    with output.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(selected)

    print(f'Input files: {len(files)}')
    print(f'Input rows: {len(raw)}')
    print(f'Industry-matched rows: {len(candidates)}')
    print(f'Unique industry-matched leads: {len(deduped)}')
    print(f'Eligible leads after email filter: {len(ranked)}')
    print(f'Exported top {len(selected)}: {output.resolve()}')
    print('Activity and website ownership require independent manual verification. No emails were sent.')
    print('Use --sync-sent after sending from Gmail to refresh the SQLite history.')
    if args.drafts:
        write_drafts(args.folder, selected)
    conn.close()
    print('\nTop 10:')
    for row in selected[:10]:
        print(f"  {row['rank']:>2}. [{row['lead_score']:>3}] {row['name']} | {row['category']} | {row['email'] or 'no email'}")




def google_review(folder, limit):
    """Create a local, no-API review dashboard with Google search links."""
    if not 1 <= limit <= 100:
        raise SystemExit('--google-review must be between 1 and 100')
    source = folder / 'top_leads.csv'
    if not source.exists():
        raise SystemExit('top_leads.csv missing. Run --rank-only --top 100 --require-email first.')
    with source.open(encoding='utf-8-sig', newline='') as handle:
        records = list(csv.DictReader(handle))
    conn = database(folder / 'lead_tracking.sqlite3')
    selected = []
    try:
        seen = set()
        for record in records:
            enrich_tracking(conn, record)
            email = normalize_email(record.get('email'))
            if (not email or email in seen or sent_to(conn, record)
                    or record['contact_status'] != 'not_contacted'
                    or record['verification_status'] in ('has_website', 'no_website_found')
                    or record['activity_status'] == 'inactive'):
                continue
            seen.add(email)
            selected.append({'lead_key': lead_key(record), 'name': record['name'],
                             'city': record.get('city', ''), 'email': email,
                             'website_search': record['search_link'],
                             'activity_search': record['activity_search_link'],
                             'status': 'skip'})
            if len(selected) >= limit:
                break
        conn.commit()
    finally:
        conn.close()
    if not selected:
        print('No unreviewed, uncontacted leads found. Refresh --rank-only if needed.')
        return
    # Embed JSON safely in a script element; do not allow lead names to close it.
    payload = json.dumps(selected, ensure_ascii=True).replace('<', '\\u003c')
    page = r"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Maier Web Solutions — Google Lead Review</title>
<style>body{font:15px system-ui,Arial;max-width:1180px;margin:32px auto;padding:0 18px;color:#1c2530;background:#f5f7fb}h1{margin-bottom:4px}p{color:#485669}table{border-collapse:collapse;width:100%;background:white}td,th{padding:12px;border-bottom:1px solid #e4e8ee;text-align:left}th{background:#eaf0f8}a{color:#125bb6}select{padding:8px;min-width:190px}button{background:#155bc1;color:white;border:0;border-radius:6px;padding:12px 18px;cursor:pointer;font-weight:600}small{color:#607080}.toolbar{position:sticky;top:0;background:#f5f7fb;padding:12px 0;display:flex;align-items:center;gap:15px;z-index:2}</style>
<h1>Maier Web Solutions — Google review</h1>
<p>Open Google for each business. Choose a result based on what YOU found. Google links do not automatically prove whether a website exists.</p>
<div class="toolbar"><button onclick="download()">Download decisions CSV</button><span id="count"></span><small>After download: py lead_finder.py --review-import google_review_decisions.csv</small></div>
<table><thead><tr><th>#</th><th>Business</th><th>Email</th><th>Google links</th><th>Your decision</th></tr></thead><tbody id="leads"></tbody></table>
<script>
const data=__PAYLOAD__;
const tbody=document.getElementById('leads');
for(let i=0;i<data.length;i++){
 const d=data[i],tr=document.createElement('tr');
 const number=document.createElement('td');number.textContent=String(i+1);tr.append(number);
 const business=document.createElement('td');business.textContent=d.name+' — '+d.city;tr.append(business);
 const email=document.createElement('td');email.textContent=d.email;tr.append(email);
 const links=document.createElement('td');
 for(const [text,url] of [['Website search',d.website_search],['Activity search',d.activity_search]]){
   const a=document.createElement('a');a.textContent=text;a.href=url;a.target='_blank';a.rel='noopener noreferrer';links.append(a,document.createTextNode('  '));
 }tr.append(links);
 const cell=document.createElement('td'),select=document.createElement('select');
 for(const [value,label] of [['skip','Not reviewed / skip'],['no_site_active','No website found + active'],['has_site','Official website found'],['uncertain','Uncertain / needs review'],['inactive','Business inactive']]){
   const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);
 }select.value=d.status;select.addEventListener('change',()=>{d.status=select.value;updateCount()});cell.append(select);tr.append(cell);tbody.append(tr);
}
function updateCount(){document.getElementById('count').textContent=data.filter(x=>x.status==='no_site_active').length+' verified eligible / '+data.length+' reviewed candidates'}
function quote(s){return '"'+String(s??'').replaceAll('"','""')+'"'}
function download(){
 const fields=['lead_key','name','city','email','status'];
 const csv=[fields.join(','),...data.map(d=>fields.map(f=>quote(d[f])).join(','))].join('\r\n');
 const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download='google_review_decisions.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
}
updateCount();
</script></html>""".replace('__PAYLOAD__', payload)
    destination = folder / 'google_review.html'
    destination.write_text(page, encoding='utf-8')
    print(f'Review dashboard: {destination.resolve()}')
    print(f'{len(selected)} businesses ready for Google review; NO emails sent.')
    print('Select decisions, download google_review_decisions.csv, move it into this folder, then run:')
    print('  py lead_finder.py --review-import google_review_decisions.csv')
    try:
        webbrowser.open(destination.resolve().as_uri())
    except Exception:
        pass


def import_google_review(folder, csv_path):
    """Import human-reviewed website decisions, matching immutable key AND email."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise SystemExit(f'File not found: {csv_path}. Move the downloaded CSV to the Marketing folder.')
    top = folder / 'top_leads.csv'
    if not top.exists():
        raise SystemExit('top_leads.csv missing. Run --rank-only first.')
    with top.open(encoding='utf-8-sig', newline='') as f:
        current = {lead_key(r): r for r in csv.DictReader(f)}
    conn = database(folder / 'lead_tracking.sqlite3')
    counts = {'no_site_active': 0, 'has_site': 0, 'uncertain': 0, 'inactive': 0, 'skip': 0}
    try:
        with csv_path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if not {'lead_key', 'email', 'status'} <= set(reader.fieldnames or []):
                raise SystemExit('Review CSV needs lead_key, email and status columns.')
            for item in reader:
                status = item['status'].strip()
                if status not in counts:
                    raise SystemExit(f'Unrecognized decision: {status!r}')
                record = current.get(item['lead_key'])
                if not record or normalize_email(record.get('email')) != normalize_email(item['email']):
                    print(f'SKIP missing/changed lead: {item.get("name", "")}')
                    continue
                enrich_tracking(conn, record)
                if sent_to(conn, record) or record['contact_status'] != 'not_contacted':
                    print(f'SKIP previously contacted: {record["name"]}')
                    continue
                key = lead_key(record)
                if status == 'no_site_active':
                    update_tracking(conn, key, 'verification_status', 'no_website_found')
                    update_tracking(conn, key, 'activity_status', 'likely_active')
                elif status == 'has_site':
                    update_tracking(conn, key, 'verification_status', 'has_website')
                elif status == 'uncertain':
                    update_tracking(conn, key, 'verification_status', 'uncertain')
                elif status == 'inactive':
                    update_tracking(conn, key, 'activity_status', 'inactive')
                counts[status] += 1
        conn.commit()
    finally:
        conn.close()
    print('Imported Google review decisions: '+', '.join(f'{k}={v}' for k,v in counts.items()))
    print('Preview: py lead_finder.py --bulk-preview 20')
    print('Send after review: py lead_finder.py --bulk-send 20')



# Free, best-effort public search. Search failures are never interpreted as no website.
SOCIAL_DOMAINS = ('facebook.com', 'instagram.com', 'tiktok.com', 'linkedin.com', 'youtube.com',
                  'x.com', 'twitter.com', 'pinterest.com', 'linktr.ee')
DIRECTORY_DOMAINS = ('yelp.com', 'yellowpages.com', 'mapquest.com', 'bbb.org', 'chamberofcommerce.com',
                     'manta.com', 'angi.com', 'thumbtack.com', 'nextdoor.com', 'google.com',
                     'bing.com', 'duckduckgo.com', 'tripadvisor.com', 'opencorporates.com',
                     'bizapedia.com', 'dnb.com', 'alignable.com', 'loc8nearme.com', 'waze.com')
GENERIC_WORDS = {'llc', 'inc', 'the', 'and', 'co', 'company', 'service', 'services', 'of', 'la',
                 'louisiana', 'shop', 'business', 'group'}


def auto_tokens(value):
    return {x for x in re.findall(r'[a-z0-9]+', (value or '').lower()) if len(x) >= 3 and x not in GENERIC_WORDS}


def auto_domain(url):
    return urlparse(url if '://' in url else 'https://' + url).netloc.lower().removeprefix('www.')


def auto_official_match(record, hit):
    url = str(hit.get('href') or hit.get('url') or '')
    domain = auto_domain(url)
    if not domain or '.' not in domain:
        return False
    if any(domain == d or domain.endswith('.' + d) for d in SOCIAL_DOMAINS + DIRECTORY_DOMAINS):
        return False
    tokens = auto_tokens(record.get('name'))
    if not tokens:
        return False
    host_tokens = auto_tokens(domain.split('.')[0].replace('-', ' '))
    title_tokens = auto_tokens(str(hit.get('title') or ''))
    overlap = len(tokens & (host_tokens | title_tokens)) / len(tokens)
    normalized_name = ''.join(re.findall(r'[a-z0-9]+', record.get('name', '').lower()))
    normalized_host = ''.join(re.findall(r'[a-z0-9]+', domain.split('.')[0]))
    if len(normalized_host) >= 6 and (normalized_host in normalized_name or normalized_name in normalized_host):
        return True
    return overlap >= 0.75 and bool(tokens & host_tokens)


def auto_research(folder, record, search_client):
    cache_dir = folder / '.lead_cache' / 'auto_web'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = re.sub(r'[^a-z0-9]+', '_', lead_key(record).lower())[:110]
    cache_file = cache_dir / (cache_key + '.json')
    if cache_file.exists() and time.time() - cache_file.stat().st_mtime < 7 * 86400:
        try:
            return json.loads(cache_file.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
    name, city = record.get('name', ''), record.get('city', '')
    # A single plain-language query is much less likely to trigger free-search
    # throttling than two consecutive heavily quoted queries per business.
    query = f'{name} {city} Louisiana'
    try:
        results = list(search_client.text(query, max_results=8) or [])
    except Exception as exc:
        # Show the actual error, so rate limits/network issues are diagnosable.
        return {'status': 'search_failed', 'url': '',
                'evidence': f'{type(exc).__name__}: {exc}'[:350]}
    if not results:
        return {'status': 'uncertain', 'url': '', 'evidence': 'Search returned zero results'}
    seen = set()
    filtered = []
    for hit in results:
        url = str(hit.get('href') or hit.get('url') or '')
        if url and url not in seen:
            seen.add(url)
            filtered.append(hit)
    official = next((h for h in filtered if auto_official_match(record, h)), None)
    if official:
        result = {'status': 'website_found', 'url': str(official.get('href') or official.get('url')),
                  'evidence': str(official.get('title') or '')[:160]}
    elif not filtered:
        result = {'status': 'uncertain', 'url': '', 'evidence': 'No search results returned'}
    else:
        # No official website surfaced in two searches. This is not proof none exists.
        # Exclude ambiguous candidates where search titles suggest a dedicated website.
        ambiguous = [h for h in filtered if auto_domain(str(h.get('href') or h.get('url') or ''))
                     and not any(auto_domain(str(h.get('href') or h.get('url') or '')) == d or
                                 auto_domain(str(h.get('href') or h.get('url') or '')).endswith('.' + d)
                                 for d in SOCIAL_DOMAINS + DIRECTORY_DOMAINS)]
        result = {'status': 'uncertain' if ambiguous else 'no_site_identified', 'url': '',
                  'evidence': f'{len(filtered)} distinct results; {len(ambiguous)} unclassified independent sites'}
    cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def auto_send(folder, limit, preview=False):
    if not 1 <= limit <= 20:
        raise SystemExit('Choose 1 to 20 emails per batch.')
    try:
        from ddgs import DDGS
    except ImportError:
        raise SystemExit('Install free search dependency first: py -m pip install ddgs')
    path = folder / 'top_leads.csv'
    if not path.exists():
        raise SystemExit('Missing top_leads.csv. Run --rank-only --top 100 --require-email first.')
    with path.open(newline='', encoding='utf-8-sig') as handle:
        records = list(csv.DictReader(handle))
    conn = database(folder / 'lead_tracking.sqlite3')
    try:
        for record in records:
            enrich_tracking(conn, record)
        conn.commit()
        service = None
        if not preview:
            print('Checking Gmail Sent before searching...')
            service = gmail_service(folder)
            sync_sent(folder, service=service, quiet=True)
        candidates = []
        report = []
        used = set()
        with DDGS() as search_client:
            for record in records:
                email = normalize_email(record.get('email'))
                if (not email or email in used or sent_to(conn, record) or
                        record.get('contact_status') != 'not_contacted' or
                        record.get('verification_status') == 'has_website' or
                        record.get('activity_status') == 'inactive'):
                    continue
                used.add(email)
                result = auto_research(folder, record, search_client)
                print(f'{record.get("name", "?")}: {result["status"]}' + (f' ({result.get("evidence", "")})' if result['status'] == 'search_failed' else ''), flush=True)
                if result['status'] == 'search_failed':
                    print('Search provider error; stopping this batch rather than repeating failed requests.')
                    report.append({'business': record.get('name', ''), 'email': email, 'city': record.get('city', ''), **result})
                    break
                report.append({'business': record.get('name', ''), 'email': email,
                               'city': record.get('city', ''), **result})
                if result['status'] in ('no_site_identified', 'uncertain'):
                    candidates.append(record)
                if len(candidates) >= limit:
                    break
                time.sleep(2.5)
        report_file = folder / 'auto_website_report.csv'
        with report_file.open('w', newline='', encoding='utf-8-sig') as handle:
            writer = csv.DictWriter(handle, fieldnames=['business', 'email', 'city', 'status', 'url', 'evidence'])
            writer.writeheader()
            writer.writerows(report)
        print(f'\nWebsite research report: {report_file.resolve()}')
        if not candidates:
            print('No sufficiently clear prospects found. Nothing sent. Search can be incomplete or blocked.')
            return
        print(f'\nCandidates (including uncertain website results): {len(candidates)}')
        for i, record in enumerate(candidates, 1):
            print(f' {i}. {record.get("name", "")} | {record.get("email", "")} | {record.get("city", "")}')
        subject, body = email_content(candidates[0])
        print(f'\nExample email:\nSubject: {subject}\n\n{body}\n')
        print('SEARCH LIMITATION: Uncertain leads may already have official websites; verify the list before approval.')
        if preview:
            print('PREVIEW ONLY. Nothing sent.')
            return
        print('These are cold commercial emails. Review recipients and honor opt-outs.')
        if input(f'Type SEND {len(candidates)} to send this batch: ').strip() != f'SEND {len(candidates)}':
            print('Cancelled. Nothing sent.')
            return
        sent = 0
        for record in candidates:
            if sent_to(conn, record):
                continue
            recipient = normalize_email(record.get('email'))
            subject, body = email_content(record)
            msg = EmailMessage()
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.set_content(body)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')
            try:
                response = service.users().messages().send(userId='me', body={'raw': raw}).execute()
            except Exception as exc:
                print(f'STOPPED: {exc}. Check Gmail Sent before retrying.')
                break
            mid = response.get('id')
            if not mid:
                print('STOPPED: No Gmail ID. Check Sent before retrying.')
                break
            now = datetime.now(timezone.utc).isoformat(timespec='seconds')
            conn.execute('INSERT OR IGNORE INTO sent_emails '
                         '(gmail_message_id, lead_key, recipient, business_name, subject, sent_at, recorded_at) '
                         'VALUES (?,?,?,?,?,?,?)',
                         (mid, lead_key(record), recipient, record.get('name', ''), subject, now, now))
            update_tracking(conn, lead_key(record), 'contact_status', 'contacted')
            conn.commit()
            sent += 1
            print(f'SENT {sent}/{len(candidates)}: {record.get("name", "")}')
            if sent < len(candidates):
                time.sleep(10)
        print(f'Finished. Sent {sent} messages.')
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Find local businesses and rank prospects in one step")
    parser.add_argument("--city", choices=CITIES, default="prairieville")
    parser.add_argument("--category", choices=["all", *KEYWORDS], default="all")
    parser.add_argument("--radius", type=int, default=5000, help="Radius in meters (250-15000)")
    parser.add_argument("--refresh", action="store_true", help="Download fresh Overture data")
    parser.add_argument("--rank-only", action="store_true", help="Rank existing leads_*.csv files without downloading")
    parser.add_argument("--top", type=int, default=50, help="Maximum ranked leads (default 50)")
    parser.add_argument("--require-email", action="store_true", help="Only rank businesses with a public email")
    parser.add_argument("--folder", type=Path, default=Path('.'), help="Folder containing leads_*.csv")
    parser.add_argument("--auto-send", type=int, metavar="N", help="Free web-search screening, then one-confirmation send up to 20")
    parser.add_argument("--auto-preview", type=int, metavar="N", help="Free web-search screening and preview only")
    parser.add_argument("--google-review", type=int, metavar="N", help="Open free Google review dashboard for up to N uncontacted leads")
    parser.add_argument("--review-import", type=Path, metavar="CSV", help="Import human website decisions downloaded from Google review dashboard")
    parser.add_argument("--lead", type=int, help="Show/update a lead by its rank in top_leads.csv")
    parser.add_argument("--gmail-send", type=int, help="Send ONE email to a manually verified lead; requires explicit confirmation")
    parser.add_argument("--bulk-send", type=int, metavar="N", help="Send up to N verified leads, max 20, after one batch confirmation")
    parser.add_argument("--quick-send", type=int, metavar="N", help="Send up to 20 uncontacted leads with public emails without manual website verification; one confirmation")
    parser.add_argument("--bulk-preview", type=int, metavar="N", help="Preview up to N verified recipients without sending")
    parser.add_argument('--sync-sent', action='store_true', help='Import Gmail Sent messages into SQLite; never send')
    parser.add_argument('--sent-report', action='store_true', help='Show previously recorded sent emails')
    parser.add_argument("--verify", choices=['not_checked', 'no_website_found', 'has_website', 'broken_website', 'uncertain'], help="Manual website review result")
    parser.add_argument("--contact", choices=['not_contacted', 'contacted', 'replied', 'customer', 'do_not_contact'], help="Update outreach status")
    parser.add_argument("--notes", help="Save notes for the selected lead")
    parser.add_argument("--drafts", action="store_true", help="Export optional CSV previews for verified leads (no Gmail drafts)")
    parser.add_argument("--activity", choices=["unknown", "likely_active", "possibly_inactive", "inactive"], help="Manual activity assessment")
    parser.add_argument("--website-url", help="Record an independently found website URL")
    parser.add_argument("--check-website", action="store_true", help="Check HTTP response for a known website")
    args = parser.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    if args.auto_send is not None or args.auto_preview is not None:
        if args.auto_send is not None and args.auto_preview is not None:
            parser.error("Choose --auto-send or --auto-preview")
        auto_send(args.folder, args.auto_preview if args.auto_preview is not None else args.auto_send, preview=args.auto_preview is not None)
        return
    if args.google_review is not None:
        google_review(args.folder, args.google_review)
        return
    if args.review_import is not None:
        import_google_review(args.folder, args.review_import)
        return
    if args.sync_sent:
        sync_sent(args.folder)
        return
    if args.sent_report:
        sent_report(args.folder)
        return
    if args.bulk_send is not None or args.bulk_preview is not None or args.quick_send is not None:
        if sum(x is not None for x in (args.bulk_send, args.bulk_preview, args.quick_send, args.gmail_send, args.lead)) != 1:
            parser.error("Choose one action: --quick-send, --bulk-send, --bulk-preview, --gmail-send, or --lead")
        limit = args.quick_send if args.quick_send is not None else (args.bulk_preview if args.bulk_preview is not None else args.bulk_send)
        bulk_send(args.folder, limit, preview=args.bulk_preview is not None,
                  quick=args.quick_send is not None)
        return
    if args.gmail_send is not None:
        if args.lead is not None:
            parser.error("Use either --lead or --gmail-send, not both")
        send_gmail_email(args.folder, args.gmail_send)
        return
    if args.lead is not None:
        manage_record(args.folder, args.lead, args.verify, args.contact, args.notes, args.activity, args.website_url, args.check_website)
        return
    if (args.verify is not None or args.contact is not None or args.notes is not None
            or args.activity is not None or args.website_url is not None or args.check_website):
        parser.error('--verify, --contact, --notes, --activity, --website-url and --check-website require --lead N')
    if not args.rank_only:
        find_args = ["--city", args.city, "--category", args.category, "--radius", str(args.radius)]
        if args.refresh:
            find_args.append("--refresh")
        finder_main(find_args)
    rank_args = ["--folder", str(args.folder), "--top", str(args.top)]
    if args.require_email:
        rank_args.append("--require-email")
    if args.drafts:
        rank_args.append("--drafts")
    print("\nRanking saved leads...")
    ranker_main(rank_args)


if __name__ == "__main__":
    main()
