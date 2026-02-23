"""
VoyageAI — API Functions v5
Amadeus = flights, Google = weather + geocoding, OpenAI = hotels/restaurants/nightlife/attractions/itinerary
"""
import requests, json

# ════════════════════════════════════════
# AMADEUS — Flights
# ════════════════════════════════════════

def get_amadeus_token(cid, cs):
    try:
        r = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token",
            data={"grant_type":"client_credentials","client_id":cid,"client_secret":cs}, timeout=10)
        if r.status_code == 200: return r.json().get("access_token")
    except: pass
    return None

def search_airports(kw, token):
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
            return out
    except: pass
    return {}

def search_flights(token, orig, dest, dep, ret, adults):
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
            return resp
        errs = r.json().get("errors",[])
        return {"_error": errs[0].get("detail","Error") if errs else f"HTTP {r.status_code}"}
    except Exception as e: return {"_error":str(e)}

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
                 attractions=None, restaurants=None, hotels=None, weather=None):
    ctx = []
    if attractions:
        ctx.append("Attractions: " + ", ".join(a.get("name","") for a in attractions[:10] if a.get("name")))
    if restaurants:
        ctx.append("Restaurants: " + ", ".join(r.get("name","") for r in restaurants[:8] if r.get("name")))
    if hotels:
        ctx.append("Hotels: " + ", ".join(h.get("name","") for h in hotels[:3] if h.get("name")))
    if weather: ctx.append(f"Weather: {weather}")

    prompt = f"""Create a detailed day-by-day travel itinerary.

TRIP: {city}, {dep} to {ret} ({days} days), {tvl} travelers
Style: {style} | Interests: {', '.join(interests)} | Food: {', '.join(food)}
Daily budget: €{daily_bud:.0f}

{"REAL DATA:" + chr(10) + chr(10).join(ctx) if ctx else ""}

For EACH day (Day 1 to Day {days}):
- Day 1 = arrival, last day = departure
- 🌅 Morning / 🌞 Afternoon / 🌙 Evening with specific REAL places
- Include restaurant names for meals
- Estimated costs per activity
- Transport tips
- Use the real places above when possible

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
