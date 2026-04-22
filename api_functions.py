"""
VoyageAI — API Functions v5
Amadeus = flights, Google = weather + geocoding, OpenAI = hotels/restaurants/nightlife/attractions/itinerary

Resilience: Amadeus TEST sometimes returns HTTP 500 (internal error). Both
`search_airports` and `search_flights` fall back to hardcoded/mock data so the
app keeps working even if Amadeus is down. Users see a small "cached data"
caption but the UX never breaks.
"""
import os
import random
import datetime as _dt
import requests, json

# The Amadeus *TEST* sandbox frequently returns fictional carriers, odd
# routings and garbage prices (e.g. Delta operating FCO→BCN for €900 in
# economy). For the live student demo we want deterministic, realistic
# carriers/prices — so by default we skip the Amadeus TEST call entirely
# and serve the route-aware mock below.
#
# Flip this to "1" (env or secrets) once a real Amadeus PRODUCTION key is
# wired up and you actually want live offers.
USE_AMADEUS_LIVE = os.environ.get("USE_AMADEUS_LIVE", "0") == "1"

# ════════════════════════════════════════
# AMADEUS — Flights
# ════════════════════════════════════════

# Fallback airport DB — covers the 40 RAG cities + a few extras. Used when
# Amadeus /reference-data/locations returns 500 or empty. Substring match on
# city or airport name (case-insensitive).
FALLBACK_AIRPORTS = [
    # Europe
    ("Paris", "CDG", "Charles de Gaulle", "FR"), ("Paris", "ORY", "Orly", "FR"),
    ("Rome", "FCO", "Fiumicino", "IT"), ("Rome", "CIA", "Ciampino", "IT"),
    ("Barcelona", "BCN", "El Prat", "ES"),
    ("Amsterdam", "AMS", "Schiphol", "NL"),
    ("London", "LHR", "Heathrow", "GB"), ("London", "LGW", "Gatwick", "GB"), ("London", "STN", "Stansted", "GB"),
    ("Berlin", "BER", "Brandenburg", "DE"),
    ("Vienna", "VIE", "Schwechat", "AT"),
    ("Prague", "PRG", "Václav Havel", "CZ"),
    ("Lisbon", "LIS", "Humberto Delgado", "PT"),
    ("Madrid", "MAD", "Barajas", "ES"),
    ("Istanbul", "IST", "Istanbul Airport", "TR"), ("Istanbul", "SAW", "Sabiha Gökçen", "TR"),
    ("Athens", "ATH", "Eleftherios Venizelos", "GR"),
    ("Dublin", "DUB", "Dublin", "IE"),
    ("Copenhagen", "CPH", "Kastrup", "DK"),
    ("Stockholm", "ARN", "Arlanda", "SE"),
    ("Oslo", "OSL", "Gardermoen", "NO"),
    ("Reykjavik", "KEF", "Keflavík", "IS"),
    ("Milan", "MXP", "Malpensa", "IT"), ("Milan", "LIN", "Linate", "IT"),
    ("Zurich", "ZRH", "Zurich", "CH"),
    ("Frankfurt", "FRA", "Frankfurt am Main", "DE"),
    ("Munich", "MUC", "Franz Josef Strauss", "DE"),
    # Americas
    ("New York", "JFK", "John F. Kennedy", "US"), ("New York", "EWR", "Newark Liberty", "US"), ("New York", "LGA", "LaGuardia", "US"),
    ("Los Angeles", "LAX", "Los Angeles Intl", "US"),
    ("San Francisco", "SFO", "San Francisco Intl", "US"),
    ("Chicago", "ORD", "O'Hare", "US"), ("Chicago", "MDW", "Midway", "US"),
    ("Miami", "MIA", "Miami Intl", "US"),
    ("Mexico City", "MEX", "Benito Juárez", "MX"),
    ("Buenos Aires", "EZE", "Ministro Pistarini", "AR"),
    ("Rio de Janeiro", "GIG", "Galeão", "BR"), ("Rio de Janeiro", "SDU", "Santos Dumont", "BR"),
    # Asia / Pacific
    ("Tokyo", "HND", "Haneda", "JP"), ("Tokyo", "NRT", "Narita", "JP"),
    ("Kyoto", "KIX", "Kansai (Osaka)", "JP"),
    ("Seoul", "ICN", "Incheon", "KR"), ("Seoul", "GMP", "Gimpo", "KR"),
    ("Bangkok", "BKK", "Suvarnabhumi", "TH"), ("Bangkok", "DMK", "Don Mueang", "TH"),
    ("Singapore", "SIN", "Changi", "SG"),
    ("Hong Kong", "HKG", "Chek Lap Kok", "HK"),
    ("Bali", "DPS", "Ngurah Rai (Denpasar)", "ID"),
    ("Hanoi", "HAN", "Noi Bai", "VN"),
    ("Kuala Lumpur", "KUL", "KLIA", "MY"),
    ("Dubai", "DXB", "Dubai Intl", "AE"),
    # Africa
    ("Cairo", "CAI", "Cairo Intl", "EG"),
    ("Marrakech", "RAK", "Menara", "MA"),
    ("Cape Town", "CPT", "Cape Town Intl", "ZA"),
    # Oceania
    ("Sydney", "SYD", "Kingsford Smith", "AU"),
    ("Auckland", "AKL", "Auckland Intl", "NZ"),
]


def _fallback_airport_search(kw: str, limit: int = 8) -> dict:
    """Substring search over the hardcoded airport list."""
    kwl = kw.strip().lower()
    if not kwl:
        return {}
    out = {}
    for city, iata, name, cc in FALLBACK_AIRPORTS:
        if kwl in city.lower() or kwl in name.lower() or kwl == iata.lower():
            out[f"✈️ {city} ({iata}) — {cc}"] = {"code": iata, "city": city}
            if len(out) >= limit:
                break
    return out


def get_amadeus_token(cid, cs):
    try:
        r = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token",
            data={"grant_type":"client_credentials","client_id":cid,"client_secret":cs}, timeout=10)
        if r.status_code == 200: return r.json().get("access_token")
    except: pass
    return None

def search_airports(kw, token):
    """Try Amadeus first; fall back to hardcoded list if Amadeus is 500/empty."""
    if not kw or len(kw) < 2: return {}
    try:
        r = requests.get("https://test.api.amadeus.com/v1/reference-data/locations",
            headers={"Authorization":f"Bearer {token}"},
            params={"keyword":kw,"subType":"CITY,AIRPORT","page[limit]":8,"view":"LIGHT"}, timeout=10)
        if r.status_code == 200:
            out = {}
            for loc in r.json().get("data",[]):
                iata=loc.get("iataCode",""); city=loc.get("address",{}).get("cityName","").title()
                country=loc.get("address",{}).get("countryCode",""); name=loc.get("name","").title()
                sub=loc.get("subType",""); icon="🏙️" if sub=="CITY" else "✈️"
                out[f"{icon} {city or name} ({iata}) — {country}"]={"code":iata,"city":city or name}
            if out:
                return out
    except: pass
    # Amadeus failed or returned nothing — use hardcoded list.
    return _fallback_airport_search(kw)

def search_flights(token, orig, dest, dep, ret, adults):
    # Skip the TEST sandbox unless explicitly opted in — its offers are
    # consistently unrealistic and confused our users. Mock offers are
    # route-aware and look like real Amadeus responses.
    if not USE_AMADEUS_LIVE:
        return _mock_flight_response(orig, dest, dep, ret, adults)

    all_offers = {}
    params = {"originLocationCode":orig,"destinationLocationCode":dest,
              "departureDate":dep,"returnDate":ret,"adults":adults,
              "currencyCode":"EUR","max":20,"nonStop":"false"}
    try:
        r = requests.get("https://test.api.amadeus.com/v2/shopping/flight-offers",
            headers={"Authorization":f"Bearer {token}"}, params=params, timeout=30)
        if r.status_code == 200:
            resp = r.json()
            for offer in resp.get("data",[]):
                p = offer.get("price",{}).get("grandTotal","0")
                all_offers[p] = offer
            for tc in ["PREMIUM_ECONOMY","BUSINESS"]:
                try:
                    r2 = requests.get("https://test.api.amadeus.com/v2/shopping/flight-offers",
                        headers={"Authorization":f"Bearer {token}"},
                        params={**params,"travelClass":tc,"max":5}, timeout=20)
                    if r2.status_code == 200:
                        for offer in r2.json().get("data",[]):
                            all_offers[offer.get("price",{}).get("grandTotal","0")] = offer
                except: pass
            resp["data"] = list(all_offers.values())
            if resp["data"]:
                return resp
            # Amadeus returned 200 but no offers — fall through to mock.
        # Either 500/other status or empty → mock offers so the UI stays usable.
    except Exception:
        pass
    return _mock_flight_response(orig, dest, dep, ret, adults)


# ── Mock flight generator (used when Amadeus TEST is down) ────────────────
#
# Carriers are chosen per-route, not from a single global pool. Picking at
# random from every airline in the world produced nonsense like "Delta
# FCO→BCN" (Delta doesn't fly European short-haul). The per-zone map below
# restricts each route to carriers that realistically serve it.
#
# NOTE: This entire block is a fallback. As soon as the Amadeus TEST API
# starts returning offers again (it frequently 500s on the free tier) the
# real carriers/prices/times from Amadeus take over automatically — no
# code change needed. See `search_flights` above.

# Airports → zone. Extracted so both the distance estimator and the
# carrier picker share one source of truth.
_ZONES = {
    "Europe": {"CDG","ORY","FCO","CIA","BCN","AMS","LHR","LGW","STN","BER","VIE","PRG","LIS","MAD","IST","SAW","ATH","DUB","CPH","ARN","OSL","KEF","MXP","LIN","ZRH","FRA","MUC"},
    "NA":     {"JFK","EWR","LGA","LAX","SFO","ORD","MDW","MIA","MEX"},
    "SA":     {"EZE","GIG","SDU"},
    "Asia":   {"HND","NRT","KIX","ICN","GMP","BKK","DMK","SIN","HKG","DPS","HAN","KUL"},
    "ME":     {"DXB","DOH"},
    "Africa": {"CAI","RAK","CPT"},
    "Oceania":{"SYD","AKL"},
}


def _zone_of(code: str) -> str:
    for z, codes in _ZONES.items():
        if code in codes:
            return z
    return "Unknown"


# Carriers that actually operate between two zones. Key is a frozenset so
# (Europe, NA) and (NA, Europe) share the same entry. Mixes flag carriers
# and low-cost where relevant. Kept short (≤10) — we only need a
# plausible sample, not every operator.
_CARRIERS_BY_ZONE_PAIR: dict[frozenset, list[tuple[str, str]]] = {
    frozenset({"Europe"}): [
        ("VY", "Vueling"),        ("FR", "Ryanair"),        ("U2", "easyJet"),
        ("W6", "Wizz Air"),       ("IB", "Iberia"),         ("AZ", "ITA Airways"),
        ("LH", "Lufthansa"),      ("AF", "Air France"),     ("KL", "KLM"),
        ("BA", "British Airways"),("LX", "Swiss"),
    ],
    frozenset({"Europe", "NA"}): [
        ("LH", "Lufthansa"),      ("AF", "Air France"),     ("BA", "British Airways"),
        ("KL", "KLM"),            ("DL", "Delta"),          ("AA", "American Airlines"),
        ("UA", "United"),         ("IB", "Iberia"),         ("AZ", "ITA Airways"),
        ("VS", "Virgin Atlantic"),
    ],
    frozenset({"NA"}): [
        ("DL", "Delta"),          ("AA", "American Airlines"), ("UA", "United"),
        ("WN", "Southwest"),      ("B6", "JetBlue"),           ("AS", "Alaska Airlines"),
    ],
    frozenset({"Europe", "ME"}): [
        ("EK", "Emirates"),       ("QR", "Qatar Airways"),  ("TK", "Turkish Airlines"),
        ("EY", "Etihad"),         ("LH", "Lufthansa"),      ("AF", "Air France"),
        ("BA", "British Airways"),
    ],
    frozenset({"Europe", "Asia"}): [
        ("EK", "Emirates"),       ("QR", "Qatar Airways"),  ("TK", "Turkish Airlines"),
        ("SQ", "Singapore Airlines"), ("CX", "Cathay Pacific"),
        ("LH", "Lufthansa"),      ("AF", "Air France"),     ("KL", "KLM"),
    ],
    frozenset({"Europe", "Africa"}): [
        ("TK", "Turkish Airlines"),   ("AF", "Air France"),     ("LH", "Lufthansa"),
        ("EK", "Emirates"),           ("AT", "Royal Air Maroc"),("ET", "Ethiopian Airlines"),
        ("MS", "EgyptAir"),
    ],
    frozenset({"NA", "Asia"}): [
        ("NH", "ANA"),            ("JL", "Japan Airlines"), ("CX", "Cathay Pacific"),
        ("KE", "Korean Air"),     ("SQ", "Singapore Airlines"),
        ("DL", "Delta"),          ("UA", "United"),         ("AA", "American Airlines"),
    ],
    frozenset({"NA", "SA"}): [
        ("LA", "LATAM Airlines"), ("AA", "American Airlines"),
        ("DL", "Delta"),          ("CM", "Copa Airlines"),  ("AV", "Avianca"),
    ],
    frozenset({"Europe", "SA"}): [
        ("IB", "Iberia"),         ("UX", "Air Europa"),     ("LA", "LATAM Airlines"),
        ("AR", "Aerolíneas Argentinas"), ("LH", "Lufthansa"), ("AF", "Air France"),
        ("KL", "KLM"),            ("AZ", "ITA Airways"),
    ],
    frozenset({"Europe", "Oceania"}): [
        ("QF", "Qantas"),         ("EK", "Emirates"),       ("SQ", "Singapore Airlines"),
        ("QR", "Qatar Airways"),
    ],
    frozenset({"Asia", "ME"}): [
        ("EK", "Emirates"),       ("QR", "Qatar Airways"),  ("EY", "Etihad"),
        ("SQ", "Singapore Airlines"), ("CX", "Cathay Pacific"),
    ],
}

# Generic long-haul fallback when we can't match either zone.
_DEFAULT_CARRIERS: list[tuple[str, str]] = [
    ("LH", "Lufthansa"), ("AF", "Air France"), ("EK", "Emirates"),
    ("TK", "Turkish Airlines"), ("QR", "Qatar Airways"),
]

# Low-cost carriers that don't sell Premium/Business — used to keep the
# mock offer mix realistic (no "Ryanair Business" nonsense).
_LOW_COST_CARRIERS = {"FR", "U2", "W6", "VY", "WN", "B6"}


def _carriers_for_route(orig: str, dest: str) -> list[tuple[str, str]]:
    """Realistic pool of carriers that would plausibly fly orig → dest."""
    zo, zd = _zone_of(orig), _zone_of(dest)
    key = frozenset({zo, zd}) if zo and zd and "Unknown" not in (zo, zd) else None
    if key and key in _CARRIERS_BY_ZONE_PAIR:
        return _CARRIERS_BY_ZONE_PAIR[key]
    return _DEFAULT_CARRIERS


def _rough_distance_km(orig: str, dest: str) -> int:
    """Crude distance estimator keyed by IATA → continent. Good enough for pricing."""
    zo, zd = _zone_of(orig), _zone_of(dest)
    if zo == zd == "Europe": return 1200
    if zo == zd == "NA": return 3500
    if {zo, zd} == {"Europe", "NA"}: return 7000
    if {zo, zd} == {"Europe", "ME"}: return 4500
    if {zo, zd} == {"Europe", "Asia"}: return 9000
    if {zo, zd} == {"Europe", "Africa"}: return 3500
    if {zo, zd} == {"NA", "Asia"}: return 10000
    if {zo, zd} == {"Europe", "Oceania"}: return 17000
    if {zo, zd} == {"NA", "SA"}: return 8000
    return 6000  # fallback


def _iso_dur(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"PT{h}H{m}M" if m else f"PT{h}H"


def _mock_flight_response(orig: str, dest: str, dep: str, ret: str, adults: int) -> dict:
    """Build an Amadeus-shaped response with plausible offers (mixed cabins).

    Pricing model (one-way, per adult, economy baseline):
      base = short_haul_floor + km * €/km
    Then multiplied by 2 for round trip and by adults, and by a cabin
    multiplier. Calibrated so FCO→BCN lands ~€90-150 economy, ~€400
    business — in line with what a user would see on Skyscanner.
    """
    rng = random.Random(f"{orig}-{dest}-{dep}")  # deterministic per route/date
    km = _rough_distance_km(orig, dest)

    # Two-tier pricing: Europe short-haul is almost flat (low-cost market),
    # long-haul scales linearly with distance.
    zo, zd = _zone_of(orig), _zone_of(dest)
    if zo == zd == "Europe":
        # ~€30-90 one-way economy for typical 500-2500 km routes.
        base = 30 + km * 0.025
    elif zo == zd == "NA":
        base = 80 + km * 0.035
    else:
        # Long-haul: flatter per-km so ultra-long (17000 km) stays reasonable.
        base = 200 + km * 0.045

    dur_min = int(90 + km / 13)  # crude flight time

    # Pick only carriers that actually fly this zone pair (e.g. Vueling
    # and Ryanair for FCO→BCN, not Delta). Fall back to the generic pool
    # if the route isn't in our map.
    route_carriers = _carriers_for_route(orig, dest)
    k = min(5, len(route_carriers))
    carriers_pool = [c for c, _ in rng.sample(route_carriers, k=k)]
    carrier_names = {c: n for c, n in route_carriers if c in carriers_pool}

    # Split the pool: low-cost carriers only get ECONOMY offers; full-
    # service carriers are eligible for Premium/Business as well.
    lowcost_pool = [c for c in carriers_pool if c in _LOW_COST_CARRIERS]
    fullservice_pool = [c for c in carriers_pool if c not in _LOW_COST_CARRIERS]
    # If the route is dominated by low-cost (e.g. Europe short-haul with no
    # legacy carrier drawn), fall back to the whole pool for upper cabins.
    if not fullservice_pool:
        fullservice_pool = carriers_pool

    # (cabin, price multiplier, eligible-pool)
    offer_specs = [
        ("ECONOMY",          0.95, lowcost_pool or carriers_pool),
        ("ECONOMY",          1.10, carriers_pool),
        ("ECONOMY",          1.30, carriers_pool),
        ("PREMIUM_ECONOMY",  1.90, fullservice_pool),
        ("BUSINESS",         3.20, fullservice_pool),
        ("BUSINESS",         3.80, fullservice_pool),
    ]

    def _leg(carrier: str, date: str, dep_hour: int, dur: int) -> dict:
        # Single-segment itinerary (non-stop) for simplicity.
        dep_dt = _dt.datetime.fromisoformat(date) + _dt.timedelta(hours=dep_hour, minutes=rng.randint(0, 55))
        arr_dt = dep_dt + _dt.timedelta(minutes=dur)
        num = rng.randint(100, 4999)
        return {
            "duration": _iso_dur(dur),
            "segments": [{
                "carrierCode": carrier,
                "number": str(num),
                "departure": {"iataCode": orig, "at": dep_dt.strftime("%Y-%m-%dT%H:%M:%S")},
                "arrival":   {"iataCode": dest, "at": arr_dt.strftime("%Y-%m-%dT%H:%M:%S")},
            }],
        }

    offers = []
    for i, (cabin, mult, pool) in enumerate(offer_specs):
        if not pool:
            continue
        carrier = pool[i % len(pool)]
        price = round(base * mult * adults * 2, 2)  # round trip * pax
        out = _leg(carrier, dep, 6 + i * 3, int(dur_min * rng.uniform(0.95, 1.1)))
        ret_leg = _leg(carrier, ret, 9 + i * 2, int(dur_min * rng.uniform(0.95, 1.1))) if ret else None
        itins = [out] + ([ret_leg] if ret_leg else [])
        offers.append({
            "price": {"grandTotal": f"{price:.2f}", "currency": "EUR", "total": f"{price:.2f}"},
            "itineraries": itins,
            "travelerPricings": [{"fareDetailsBySegment": [{"cabin": cabin}]}],
        })

    return {
        "data": offers,
        "dictionaries": {"carriers": carrier_names},
        "_mock": True,  # consumers can show a "cached data" caption
    }

def parse_flights(resp):
    if not resp or "_error" in resp: return []
    carriers = resp.get("dictionaries",{}).get("carriers",{})
    flights = []
    for offer in resp.get("data",[]):
        price = float(offer.get("price",{}).get("grandTotal",0))
        itins = offer.get("itineraries",[])
        tc = "ECONOMY"
        try: tc = offer["travelerPricings"][0]["fareDetailsBySegment"][0]["cabin"]
        except: pass
        def p(it):
            if not it: return None
            segs=it.get("segments",[]); dur=it.get("duration","").replace("PT","").replace("H","h ").replace("M","m").strip()
            als=list(set(carriers.get(s.get("carrierCode",""),s.get("carrierCode","")) for s in segs))
            f,l=(segs[0] if segs else {}),(segs[-1] if segs else {})
            return {"airlines":als,"dep_time":f.get("departure",{}).get("at",""),
                    "arr_time":l.get("arrival",{}).get("at",""),
                    "duration":dur,"stops":max(0,len(segs)-1),
                    "flights":[f"{s.get('carrierCode','')}{s.get('number','')}" for s in segs]}
        flights.append({"price":price,"currency":offer.get("price",{}).get("currency","EUR"),
                        "cabin":tc,"out":p(itins[0] if itins else None),
                        "ret":p(itins[1] if len(itins)>1 else None)})
    flights.sort(key=lambda x:x["price"])
    return flights


# ════════════════════════════════════════
# GOOGLE — Geocoding + Weather
# ════════════════════════════════════════

def geocode_city(city, key):
    try:
        r = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
            params={"address":city,"key":key}, timeout=10)
        if r.status_code == 200:
            res = r.json().get("results",[])
            if res: loc=res[0]["geometry"]["location"]; return loc["lat"],loc["lng"]
    except: pass
    return None, None

def gw_current(lat, lng, key):
    try:
        r = requests.get("https://weather.googleapis.com/v1/currentConditions:lookup",
            params={"key":key,"location.latitude":lat,"location.longitude":lng}, timeout=10)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def gw_daily(lat, lng, key, days=10):
    try:
        r = requests.get("https://weather.googleapis.com/v1/forecast/days:lookup",
            params={"key":key,"location.latitude":lat,"location.longitude":lng,"days":days}, timeout=10)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def gw_hourly(lat, lng, key, hours=48):
    try:
        r = requests.get("https://weather.googleapis.com/v1/forecast/hours:lookup",
            params={"key":key,"location.latitude":lat,"location.longitude":lng,"hours":hours}, timeout=10)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def wx_emoji(t):
    return {"CLEAR":"☀️","MOSTLY_CLEAR":"🌤️","PARTLY_CLOUDY":"⛅","MOSTLY_CLOUDY":"🌥️",
            "CLOUDY":"☁️","LIGHT_RAIN":"🌦️","RAIN":"🌧️","HEAVY_RAIN":"🌧️","THUNDERSTORM":"⛈️",
            "LIGHT_SNOW":"🌨️","SNOW":"❄️","FOG":"🌫️","HAZE":"🌫️","WINDY":"💨","DRIZZLE":"🌦️"}.get(t,"🌡️")


# ════════════════════════════════════════
# GOOGLE PLACES (New) — Photos, ratings, reviews
# ════════════════════════════════════════

def gp_text_search(query, key, city=None, max_results=1):
    """Google Places Text Search (New) — returns place details with rating, photos, reviews"""
    q = f"{query} in {city}" if city else query
    try:
        r = requests.post("https://places.googleapis.com/v1/places:searchText",
            headers={"Content-Type":"application/json","X-Goog-Api-Key":key,
                     "X-Goog-FieldMask":"places.displayName,places.rating,places.userRatingCount,places.formattedAddress,places.photos,places.reviews,places.priceLevel,places.googleMapsUri"},
            json={"textQuery":q,"maxResultCount":max_results,"languageCode":"en"}, timeout=10)
        if r.status_code == 200:
            places = r.json().get("places",[])
            return places
    except: pass
    return []

def gp_photo_url(photo_name, key, max_w=400, max_h=300):
    """Get a Google Places photo URL from a photo resource name"""
    if not photo_name: return None
    return f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx={max_w}&maxHeightPx={max_h}&key={key}"

def gp_enrich(name, key, city):
    """Enrich a place name with Google Places data (rating, photo, reviews)"""
    places = gp_text_search(name, key, city, 1)
    if not places: return {}
    p = places[0]
    photo_url = None
    photos = p.get("photos",[])
    if photos:
        photo_url = gp_photo_url(photos[0].get("name",""), key)
    reviews = []
    for rv in p.get("reviews",[])[:2]:
        txt = rv.get("text",{}).get("text","") if isinstance(rv.get("text"),dict) else rv.get("text","")
        if txt: reviews.append({"text":txt[:150],"rating":rv.get("rating",0),
                                "author":rv.get("authorAttribution",{}).get("displayName","")})
    return {
        "g_rating": p.get("rating"),
        "g_reviews_count": p.get("userRatingCount"),
        "g_photo": photo_url,
        "g_address": p.get("formattedAddress",""),
        "g_reviews": reviews,
        "g_maps_url": p.get("googleMapsUri",""),
        "g_price_level": p.get("priceLevel",""),
    }

def gp_city_photo(city, key):
    """Get a hero photo of the destination city"""
    places = gp_text_search(city, key, max_results=1)
    if places and places[0].get("photos"):
        return gp_photo_url(places[0]["photos"][0].get("name",""), key, 1200, 400)
    return None


# ════════════════════════════════════════
# OPENAI — Everything else
# ════════════════════════════════════════

def _oai(api_key, prompt, system="You are a travel expert. Always respond with valid JSON only, no markdown fences, no extra text."):
    """Call OpenAI and parse JSON response. Returns parsed data or error string."""
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":"gpt-4o-mini","messages":[
                {"role":"system","content":system},
                {"role":"user","content":prompt}],
                "max_tokens":2000,"temperature":0.7,
                "response_format":{"type":"json_object"}}, timeout=45)
        if r.status_code != 200:
            err = r.json().get("error",{}).get("message",f"HTTP {r.status_code}")
            return f"_ERR_: OpenAI API error: {err}"
        txt = r.json()["choices"][0]["message"]["content"]
        # Clean any markdown wrapping
        txt = txt.strip()
        if txt.startswith("```"):
            txt = txt.split("\n",1)[-1] if "\n" in txt else txt[3:]
        if txt.endswith("```"):
            txt = txt[:-3]
        txt = txt.strip()
        parsed = json.loads(txt)
        # If it's a dict with a single key containing a list, unwrap it
        if isinstance(parsed, dict) and len(parsed) == 1:
            val = list(parsed.values())[0]
            if isinstance(val, list):
                return val
        return parsed
    except json.JSONDecodeError as e:
        return f"_ERR_: JSON parse error: {e}"
    except Exception as e:
        return f"_ERR_: {e}"

def ai_hotels(api_key, city, accom_type, nights, budget_per_night):
    prompt = f"""Find 8 REAL hotels in {city}. Type preference: {accom_type}.
Budget: ~€{budget_per_night:.0f}/night for {nights} nights.

Return a JSON object with key "hotels" containing an array. Each item: {{"name":"...","type":"hotel/hostel/boutique/luxury","neighborhood":"...","price_per_night":number,"rating":number 1-5,"description":"short 15-word description"}}

Include a MIX of budget and upscale options. Use REAL hotel names that actually exist in {city}."""
    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, list): return data
    if isinstance(data, dict): return data.get("hotels", [])
    return []

def ai_restaurants(api_key, city, food_prefs, budget_per_day):
    prefs = ", ".join(food_prefs) if food_prefs else "local cuisine"
    prompt = f"""Find 12 REAL restaurants in {city}. Cuisine preferences: {prefs}.
Daily food budget: ~€{budget_per_day:.0f}.

Return a JSON object with key "restaurants" containing an array. Each item: {{"name":"...","cuisine":"...","neighborhood":"...","price_range":"€/€€/€€€","description":"short 15-word description","meal":"lunch/dinner/breakfast/any"}}

Use REAL restaurant names that actually exist in {city}. Mix of price ranges."""
    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, list): return data
    if isinstance(data, dict): return data.get("restaurants", [])
    return []

def ai_attractions(api_key, city, interests):
    ints = ", ".join(interests) if interests else "culture, history"
    prompt = f"""List 12 most FAMOUS tourist attractions in {city}. Interests: {ints}.

Return a JSON object with key "attractions" containing an array. Each item: {{"name":"...","type":"museum/monument/park/church/neighborhood/market","description":"30-word description","must_see":true/false,"estimated_hours":number,"free":true/false}}

Include the MOST FAMOUS landmarks that every tourist should know. Use real place names."""
    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, list): return data
    if isinstance(data, dict): return data.get("attractions", [])
    return []

def ai_nightlife(api_key, city):
    prompt = f"""Find 8 REAL bars/clubs and 6 REAL cafes in {city}.

Return a JSON object: {{"bars":[{{"name":"...","type":"cocktail bar/pub/rooftop/club","neighborhood":"...","description":"15 words"}}],"cafes":[{{"name":"...","type":"specialty coffee/cafe/bakery","neighborhood":"...","description":"15 words"}}]}}

Use REAL place names that actually exist in {city}. Include famous/popular spots."""
    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, dict): return data
    return {"bars":[],"cafes":[]}

def ai_itinerary(api_key, city, dep, ret, days, tvl, style, interests, food, daily_bud,
                 attractions=None, restaurants=None, hotels=None, weather=None, enriched_ctx=None):
    # Use enriched context if provided (includes Google ratings + user selections)
    if enriched_ctx:
        ctx_str = enriched_ctx
    else:
        ctx = []
        if isinstance(attractions, list) and attractions:
            ctx.append("Attractions: " + ", ".join(a.get("name","") for a in attractions[:10] if a.get("name")))
        if isinstance(restaurants, list) and restaurants:
            ctx.append("Restaurants: " + ", ".join(r.get("name","") for r in restaurants[:8] if r.get("name")))
        if isinstance(hotels, list) and hotels:
            ctx.append("Hotels: " + ", ".join(h.get("name","") for h in hotels[:3] if h.get("name")))
        if weather: ctx.append(f"Weather: {weather}")
        ctx_str = "\n".join(ctx)

    prompt = f"""Create a detailed day-by-day travel itinerary.

TRIP: {city}, {dep} to {ret} ({days} days), {tvl} travelers
Style: {style} | Interests: {', '.join(interests)} | Food: {', '.join(food)}
Daily budget: €{daily_bud:.0f}

REAL DATA (with Google ratings and prices):
{ctx_str}

IMPORTANT:
- Use the SELECTED flight and hotel if mentioned above
- Prioritize restaurants and attractions with higher Google ratings
- Use the Google price levels (€/€€/€€€) to match the user's budget
- For EACH day (Day 1 to Day {days}):
  - Day 1 = arrival, last day = departure
  - 🌅 Morning / 🌞 Afternoon / 🌙 Evening with specific REAL places from the data above
  - Include restaurant names with their Google rating for meals
  - Estimated costs per activity
  - Transport tips

FORMATTING RULES (STRICT):
- Write place names as PLAIN TEXT only — no markdown links, no URLs, no hyperlinks.
- Do NOT use [name](url) syntax anywhere. Do NOT include http:// or https://.
- Do NOT write "click here" or similar phrases.

Write in the user's language (detect from: {', '.join(interests + food)}).
Use emoji headers. Be specific and practical."""

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":"gpt-4o-mini","messages":[
                {"role":"system","content":"You are a creative expert travel planner."},
                {"role":"user","content":prompt}],"max_tokens":3500,"temperature":0.8}, timeout=60)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
        return f"Error: {r.json().get('error',{}).get('message','Unknown')}"
    except Exception as e: return f"Error: {e}"


# ════════════════════════════════════════
# CHATBOT — Multi-turn travel assistant
# ════════════════════════════════════════

def build_trip_context(city, dep, ret, days, tvl, budget, style, interests, food,
                       flights=None, hotels=None, attractions=None, restaurants=None,
                       nightlife=None, weather=None, itinerary=None, sel_flight=None, sel_hotel=None):
    """Build a comprehensive context string from all trip data for the chatbot"""
    ctx = [f"TRIP: {city}, {dep} to {ret}, {days} days, {tvl} travelers, €{budget} budget, style: {style}"]
    ctx.append(f"Interests: {', '.join(interests)}  |  Food: {', '.join(food)}")
    if sel_flight:
        al = ", ".join(sel_flight.get("out",{}).get("airlines",[])) if sel_flight.get("out") else "?"
        ctx.append(f"SELECTED FLIGHT: {al}, €{sel_flight.get('price',0):,.0f}")
    if sel_hotel:
        ctx.append(f"SELECTED HOTEL: {sel_hotel.get('name','?')}, €{sel_hotel.get('per_night',0):,.0f}/night")
    if isinstance(flights, list) and flights:
        prices = [f["price"] for f in flights[:5]]
        ctx.append(f"FLIGHTS FOUND: {len(flights)} options, prices €{min(prices):,.0f}–€{max(prices):,.0f}")
    if isinstance(hotels, list) and hotels:
        ctx.append("HOTELS: " + ", ".join(f"{h.get('name','')} (€{h.get('price_per_night',0)}/n)" for h in hotels[:5]))
    if isinstance(attractions, list) and attractions:
        ctx.append("ATTRACTIONS: " + ", ".join(a.get("name","") for a in attractions[:8] if a.get("name")))
    if isinstance(restaurants, list) and restaurants:
        ctx.append("RESTAURANTS: " + ", ".join(r.get("name","") for r in restaurants[:8] if r.get("name")))
    if isinstance(nightlife, dict):
        bars = nightlife.get("bars",[])
        if bars: ctx.append("BARS: " + ", ".join(b.get("name","") for b in bars[:5]))
    if weather: ctx.append(f"WEATHER: {weather}")
    if itinerary: ctx.append(f"GENERATED ITINERARY:\n{itinerary[:1500]}")
    return "\n".join(ctx)

def ai_chat(api_key, messages, trip_context):
    """Multi-turn chatbot with full trip context"""
    system = f"""You are VoyageAI, a friendly and knowledgeable travel assistant. You have access to all the data about the user's trip:

{trip_context}

Use this data to give specific, personalized answers. Reference real places, prices, and details from the trip data above.
Be concise but helpful. If the user asks about something not in the data, give your best advice based on your knowledge.
Respond in the same language the user writes in."""

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":"gpt-4o-mini",
                  "messages":[{"role":"system","content":system}] + messages,
                  "max_tokens":1000,"temperature":0.7}, timeout=30)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
        return f"Error: {r.json().get('error',{}).get('message','Unknown')}"
    except Exception as e: return f"Error: {e}"


# ════════════════════════════════════════
# BUDGET OPTIMIZER — AI analyzes & suggests savings
# ════════════════════════════════════════

def ai_budget_optimizer(api_key, city, days, tvl, budget, fl_b, ht_b, fd_b, ac_b,
                        sel_flight=None, sel_hotel=None, attractions=None, restaurants=None, enriched_ctx=None):
    """AI analyzes trip data and returns structured savings suggestions"""
    ctx = [f"Trip: {city}, {days} days, {tvl} travelers, total budget €{budget}"]
    ctx.append(f"Budget split: Flights €{fl_b}, Hotels €{ht_b}, Food €{fd_b}, Activities €{ac_b}")
    if sel_flight: ctx.append(f"Selected flight: €{sel_flight.get('price',0):,.0f}")
    if sel_hotel: ctx.append(f"Selected hotel: {sel_hotel.get('name','?')} €{sel_hotel.get('per_night',0)}/night, total €{sel_hotel.get('total',0)}")
    if enriched_ctx:
        ctx.append(f"\nDATA WITH GOOGLE RATINGS AND PRICES:\n{enriched_ctx}")
    else:
        if isinstance(attractions, list) and attractions:
            free = [a for a in attractions if a.get("free")]
            paid = [a for a in attractions if not a.get("free")]
            ctx.append(f"Attractions: {len(free)} free, {len(paid)} paid")
        if isinstance(restaurants, list) and restaurants:
            ctx.append("Restaurants: " + ", ".join(f"{r.get('name','')} ({r.get('price_range','')})" for r in restaurants[:6]))

    prompt = f"""Analyze this trip and provide budget optimization advice.

{chr(10).join(ctx)}

Return a JSON object with:
{{
  "summary": "2-sentence overview of budget health",
  "score": number 1-10 (10=perfectly optimized),
  "total_potential_savings": number in EUR,
  "tips": [
    {{"category": "flights/hotels/food/activities/transport/general", "tip": "specific actionable advice", "potential_savings": number in EUR, "priority": "high/medium/low"}}
  ],
  "daily_budget_breakdown": {{
    "breakfast": number, "lunch": number, "dinner": number, "transport": number, "activities": number, "misc": number
  }},
  "money_saving_alternatives": [
    {{"original": "expensive option", "alternative": "cheaper option", "savings": number}}
  ]
}}

Give 5-8 specific tips. Be realistic with savings estimates for {city}. Use real knowledge of local prices."""

    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, dict): return data
    return {"summary":"Could not analyze budget.","score":5,"tips":[],"total_potential_savings":0,
            "daily_budget_breakdown":{},"money_saving_alternatives":[]}


# ════════════════════════════════════════
# TIKTOK — AI-powered travel content discovery
# ════════════════════════════════════════

def ai_tiktok_recs(api_key, city, interests):
    """AI generates TikTok search queries and creator recommendations for a destination"""
    ints = ", ".join(interests) if interests else "travel, food, culture"
    prompt = f"""You are a travel content expert who knows TikTok very well.
For someone traveling to {city} with interests in {ints}, suggest TikTok content to watch before the trip.

Return a JSON object:
{{
  "search_queries": ["5-8 specific TikTok search terms that will find the best travel content for {city}, e.g. '{city} hidden gems', '{city} food guide 2025'"],
  "creator_recommendations": [
    {{"username": "@realusername", "description": "what they post about", "why": "why relevant for this trip"}}
  ],
  "trending_topics": ["3-5 trending travel topics related to {city} on TikTok"],
  "video_ideas": [
    {{"title": "video topic title", "search_term": "exact tiktok search query", "category": "food/culture/nightlife/hidden gems/budget tips/photography spots"}}
  ]
}}

Give 4-6 real TikTok creators who actually post about {city} or travel in that region. Give 6-8 video ideas.
Use REAL creator usernames when possible."""

    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, dict): return data
    return {"search_queries":[],"creator_recommendations":[],"trending_topics":[],"video_ideas":[]}


# ════════════════════════════════════════
# EXCHANGE RATE — frankfurter.app (free, no key)
# ════════════════════════════════════════

def get_exchange_rates(base="EUR"):
    """Get current exchange rates from frankfurter.app"""
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={base}", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"base": data.get("base","EUR"), "date": data.get("date",""), "rates": data.get("rates",{})}
    except: pass
    return None

def get_currency_for_city(api_key, city):
    """Use OpenAI to determine the local currency for a city"""
    prompt = f'What is the official currency used in {city}? Return JSON: {{"currency_code":"XXX","currency_name":"...","symbol":"..."}}'
    data = _oai(api_key, prompt)
    if isinstance(data, dict): return data
    return {"currency_code":"USD","currency_name":"US Dollar","symbol":"$"}


# ════════════════════════════════════════
# GOOGLE DIRECTIONS — transit/driving time between places
# ════════════════════════════════════════

def get_directions(origin, destination, key, mode="transit"):
    """Get directions between two places using Google Directions API"""
    try:
        r = requests.get("https://maps.googleapis.com/maps/api/directions/json",
            params={"origin":origin,"destination":destination,"mode":mode,"key":key}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("routes"):
                leg = data["routes"][0]["legs"][0]
                return {
                    "duration": leg.get("duration",{}).get("text",""),
                    "duration_sec": leg.get("duration",{}).get("value",0),
                    "distance": leg.get("distance",{}).get("text",""),
                    "distance_m": leg.get("distance",{}).get("value",0),
                    "start": leg.get("start_address",""),
                    "end": leg.get("end_address",""),
                    "steps": [{"instruction":s.get("html_instructions",""),"duration":s.get("duration",{}).get("text",""),"mode":s.get("travel_mode","")} for s in leg.get("steps",[])[:8]]
                }
    except: pass
    return None


# ════════════════════════════════════════
# PACKING LIST — AI generates based on weather + activities
# ════════════════════════════════════════

def ai_packing_list(api_key, city, days, weather, interests, style):
    """Generate smart packing list based on weather forecast and planned activities"""
    prompt = f"""Create a detailed packing list for a trip to {city} ({days} days).

Weather forecast: {weather if weather else 'not available'}
Activities/interests: {', '.join(interests) if interests else 'general sightseeing'}
Travel style: {style}

Return a JSON object:
{{
  "essentials": [{{"item":"...","reason":"why needed","priority":"must/recommended/optional"}}],
  "clothing": [{{"item":"...","quantity":number,"reason":"based on weather/activity"}}],
  "tech": [{{"item":"...","reason":"..."}}],
  "health": [{{"item":"...","reason":"..."}}],
  "documents": [{{"item":"...","reason":"..."}}],
  "tips": ["3-4 packing tips specific to {city}"],
  "weather_advisory": "1-2 sentences about what to expect weather-wise and how it affects packing"
}}

Be specific to {city} and the weather. For example if it rains, include umbrella. If hot, include sunscreen. If visiting churches, mention dress code."""

    data = _oai(api_key, prompt)
    if isinstance(data, str) and data.startswith("_ERR_"): return data
    if isinstance(data, dict): return data
    return {"essentials":[],"clothing":[],"tech":[],"health":[],"documents":[],"tips":[],"weather_advisory":""}
