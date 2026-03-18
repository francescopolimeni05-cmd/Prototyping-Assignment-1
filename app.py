"""
✈️ VoyageAI — AI-Powered Travel Planner v6
APIs: Amadeus (flights) · Google Weather · Google Places (photos+ratings+reviews) · OpenAI (content+itinerary)
Streamlit widgets: map, metrics, charts, progress bars, expanders, columns, download, tabs
"""
import streamlit as st
import json, os, time
from datetime import timedelta, date
import pandas as pd
from api_functions import *

st.set_page_config(page_title="VoyageAI", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

def K(n):
    try: return st.secrets[n]
    except: return os.environ.get(n, "")

AMA_ID=K("AMADEUS_CLIENT_ID"); AMA_SEC=K("AMADEUS_CLIENT_SECRET")
GKEY=K("GOOGLE_API_KEY"); OAIKEY=K("OPENAI_API_KEY")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
.main{background-color:#f5f5f5}
.main .block-container{padding-top:1.5rem;max-width:1200px}
h1,h2,h3{font-family:'Playfair Display',serif!important;color:#003580}
p,li,span,div{font-family:'Inter',sans-serif}

/* Hero */
.hero{font-family:'Playfair Display',serif;font-size:3.2rem;font-weight:700;color:#003580;text-align:center;margin-bottom:0;letter-spacing:-1px}
.sub{text-align:center;color:#6b6b6b;margin-bottom:2rem;font-size:1rem;letter-spacing:.5px}

/* Cards - Booking.com style */
.fc{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:1.5rem;margin-bottom:1rem;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:all .2s ease}
.fc:hover{box-shadow:0 4px 16px rgba(0,53,128,.15);border-color:#003580}
.pt{font-family:'Inter',sans-serif;font-size:1.8rem;font-weight:700;color:#003580}
.an{font-weight:600;font-size:1.05rem;color:#1a1a1a}
.ri{color:#555;font-size:.9rem;line-height:1.5}

/* Weather card - Booking blue */
.wc{background:linear-gradient(135deg,#003580 0%,#00224f 100%);border-radius:8px;padding:2rem;color:#fff;text-align:center;margin-bottom:1rem;box-shadow:0 4px 12px rgba(0,53,128,.3)}
.wt{font-family:'Inter',sans-serif;font-size:2.8rem;font-weight:700}

/* Place card */
.pc{background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:1.1rem;margin-bottom:.8rem;box-shadow:0 1px 4px rgba(0,0,0,.05);transition:all .2s ease}
.pc:hover{box-shadow:0 2px 8px rgba(0,53,128,.12);border-color:#003580}

/* Badge - Booking style */
.cb{display:inline-block;background:#003580;color:#fff;padding:.2rem .6rem;border-radius:4px;font-size:.72rem;font-weight:600;margin-right:.3rem;margin-bottom:.3rem}

/* Metric card */
.mc{background:#003580;border-radius:8px;padding:1.1rem;text-align:center}
.mv{font-family:'Inter',sans-serif;font-size:1.5rem;font-weight:700;color:#fff}
.ml{font-size:.82rem;color:rgba(255,255,255,.7);margin-top:.2rem}

/* Stars - Booking yellow */
.stars{color:#febb02;font-size:1.05rem;letter-spacing:1px}

/* Sidebar - Dark blue Booking */
div[data-testid="stSidebar"]{background:#003580}
div[data-testid="stSidebar"] p,div[data-testid="stSidebar"] label,div[data-testid="stSidebar"] h1,div[data-testid="stSidebar"] h2,div[data-testid="stSidebar"] h3{color:#fff!important}
div[data-testid="stSidebar"] .stMarkdown h2{font-size:1.3rem}

/* Tabs - Booking style */
button[data-baseweb="tab"]{font-family:'Inter',sans-serif!important;font-weight:500;font-size:.85rem;color:#003580!important}
div[data-baseweb="tab-highlight"]{background-color:#003580!important}

/* Expanders */
details{border:1px solid #e0e0e0!important;border-radius:8px!important;background:#fff!important;margin-bottom:.5rem}
details summary{font-weight:600;padding:.8rem}

/* Chat */
div[data-testid="stChatMessage"]{border-radius:8px;margin-bottom:.5rem}

/* Primary button - Booking blue */
.stButton>button[kind="primary"]{background:#003580!important;border:none!important;border-radius:4px!important;font-weight:600!important;letter-spacing:.3px;color:#fff!important}
.stButton>button[kind="primary"]:hover{background:#00224f!important;box-shadow:0 2px 8px rgba(0,53,128,.3)!important;color:#fff!important}

/* Secondary buttons */
.stButton>button:not([kind="primary"]){border-radius:4px!important;border:1px solid #003580!important;color:#003580!important;background:#fff!important}
.stButton>button:not([kind="primary"]):hover{background:#f0f4ff!important}

/* Metrics - Booking style */
div[data-testid="stMetric"]{background:#fff;border-radius:8px;padding:.8rem;border:1px solid #e0e0e0}
div[data-testid="stMetric"] label{font-size:.8rem;color:#6b6b6b}
div[data-testid="stMetric"] div[data-testid="stMetricValue"]{font-family:'Inter',sans-serif;color:#003580;font-weight:700}

/* Progress bar - Booking blue */
div[data-testid="stProgress"]>div>div{background:#003580!important;border-radius:4px}

/* Images */
div[data-testid="stImage"] img{border-radius:8px}

/* Download buttons */
.stDownloadButton>button{border-radius:4px!important;border:1px solid #003580!important;color:#003580!important;background:#fff!important}
.stDownloadButton>button:hover{background:#f0f4ff!important}

/* Progress bar text fix */
div[data-testid="stProgress"] p{color:#fff!important;font-weight:600;text-shadow:0 1px 2px rgba(0,0,0,.3)}

/* Info/Success/Warning boxes */
div[data-testid="stAlert"]{border-radius:8px}

/* Scrollbar */
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-thumb{background:#003580;border-radius:3px}

/* Yellow accent for special elements */
.booking-yellow{background:#febb02;color:#003580;font-weight:700;padding:.3rem .8rem;border-radius:4px;display:inline-block}
</style>""", unsafe_allow_html=True)

# helper: render star rating
def stars_html(rating, count=None):
    if not rating: return ""
    full = int(rating); half = 1 if rating - full >= 0.3 else 0
    s = "★" * full + ("½" if half else "") + "☆" * (5 - full - half)
    c = f' <span style="font-size:.8rem;color:#888">({count})</span>' if count else ""
    return f'<span class="stars">{s}</span> <b>{rating}</b>{c}'

# Amadeus auth
amadeus_token = None
if AMA_ID and AMA_SEC:
    ck=(AMA_ID,AMA_SEC)
    if "atk" not in st.session_state or st.session_state.get("_ck")!=ck:
        t=get_amadeus_token(AMA_ID,AMA_SEC)
        if t: st.session_state.atk=t; st.session_state._ck=ck
    amadeus_token=st.session_state.get("atk")

# ═══ SIDEBAR ═══
with st.sidebar:
    apis={"Amadeus":bool(amadeus_token),"Google":bool(GKEY),"OpenAI":bool(OAIKEY)}
    miss=[n for n,v in apis.items() if not v]
    if not miss: st.success("All APIs ready ✅")
    else: st.warning(f"Missing: {', '.join(miss)}")
    st.markdown("---")
    st.markdown("## 🧳 Trip Setup")
    def apick(label, sk):
        q=st.text_input(label,key=f"{sk}_q",placeholder="City name or airport code (e.g. Rome, JFK)...")
        if amadeus_token and q and len(q)>=2:
            # Search with exact input + also try with common variations
            ck=f"_ap_{sk}_{q.strip()}"
            if ck not in st.session_state:
                results = search_airports(q.strip(), amadeus_token)
                # If no results, try capitalizing first letter
                if not results and not q[0].isupper():
                    results = search_airports(q.strip().title(), amadeus_token)
                st.session_state[ck] = results
            res=st.session_state[ck]
            if res:
                sel=st.selectbox("✈️ Select airport:",list(res.keys()),key=f"{sk}_s",label_visibility="collapsed")
                return res[sel]["code"],res[sel]["city"]
            else:
                st.caption("⚠️ No airports found. Try English name or IATA code.")
        return None,q
    orig_code,orig_city=apick("🛫 Departure","orig")
    dest_code,dest_city=apick("🛬 Destination","dest")
    st.markdown("---")
    c1,c2=st.columns(2)
    with c1: dep_date=st.date_input("📅 Depart",value=date.today()+timedelta(7),min_value=date.today())
    with c2: ret_date=st.date_input("📅 Return",value=date.today()+timedelta(14),min_value=dep_date+timedelta(1))
    trip_days=(ret_date-dep_date).days
    travelers=st.slider("👥 Travelers",1,8,2)
    budget=st.number_input("💰 Budget (EUR)",100,50000,2000,100)
    st.markdown("---")
    st.markdown("## 🎯 Preferences")
    style=st.select_slider("Style",["🏖️ Relax","⚖️ Balanced","🏃 Adventure"],"⚖️ Balanced")
    interests=st.multiselect("Interests",["🏛️ Culture","🍽️ Food","🌿 Nature","🛍️ Shopping","🎭 Nightlife","🏖️ Beaches","🎨 Art","⛪ Architecture"],default=["🏛️ Culture","🍽️ Food"])
    food_prefs=st.multiselect("Food",["🍕 Italian","🍣 Japanese","🥘 Local","🥗 Vegetarian","🍔 Fast Food","☕ Cafes","🍷 Wine","🧁 Pastry"],default=["🥘 Local"])
    accom=st.radio("Accommodation",["🏨 Hotel","🏠 Apartment","🏡 Hostel","✨ Luxury"],horizontal=True)
    st.markdown("---")
    st.markdown("### 💸 Budget")
    fl_pct=st.slider("Flights %",10,70,40,5); ht_pct=st.slider("Accom %",10,60,30,5); fd_pct=st.slider("Food %",5,40,20,5)
    ac_pct=max(0,100-fl_pct-ht_pct-fd_pct)
    if ac_pct==0: st.warning("⚠️ >100%!")
    st.info(f"Activities: **{ac_pct}%**")
    fl_b,ht_b,fd_b,ac_b=[int(budget*p/100) for p in [fl_pct,ht_pct,fd_pct,ac_pct]]
    # Budget donut-style progress
    st.progress(min(fl_pct+ht_pct+fd_pct,100)/100, text=f"Allocated: {fl_pct+ht_pct+fd_pct}%")

    go=st.button("🔍 Plan My Trip!",use_container_width=True,type="primary")
    if go:
        for k in ["flights_data","hotels_data","wx_data","attr_data","rest_data","night_data","ai_itinerary","geo","city_photo","gp_cache","chat_messages","budget_analysis","tiktok_data","all_loaded","pending_chat","local_currency","exchange_rates","last_directions","packing_data"]:
            st.session_state.pop(k,None)
        st.session_state.search_done=True
        st.session_state.sp={"oc":orig_code,"dc":dest_code,"ocity":orig_city,"dcity":dest_city,
            "dep":dep_date,"ret":ret_date,"tvl":travelers,"bud":budget,
            "fl_b":fl_b,"ht_b":ht_b,"fd_b":fd_b,"ac_b":ac_b}

# ═══ MAIN ═══
st.markdown('<p class="hero">✈️ VoyageAI</p>',unsafe_allow_html=True)
st.markdown('<p class="sub">AI-Powered Travel Planner · Real Flights · Google Reviews · Smart Recommendations</p>',unsafe_allow_html=True)

if not st.session_state.get("search_done"):
    st.markdown("""<div style="text-align:center;padding:3rem 1rem;background:#003580;border-radius:8px;margin:2rem 0">
    <div style="font-size:3rem;margin-bottom:1rem">✈️</div>
    <div style="font-family:'Playfair Display',serif;font-size:1.8rem;font-weight:700;color:#fff;margin-bottom:.5rem">Where do you want to go?</div>
    <div style="color:rgba(255,255,255,.8);max-width:500px;margin:0 auto">Set up your trip in the sidebar and click <b style="color:#febb02">Plan My Trip</b> to get AI-powered recommendations, real flights, Google reviews, weather forecasts, and a personalized itinerary.</div>
    </div>""", unsafe_allow_html=True)
    f1,f2,f3,f4=st.columns(4)
    with f1: st.markdown('<div style="text-align:center;padding:1rem;background:#fff;border-radius:8px;border:1px solid #e0e0e0"><div style="font-size:2rem">✈️</div><div style="font-weight:700;color:#003580">Real Flights</div><div style="font-size:.8rem;color:#6b6b6b">Amadeus API</div></div>',unsafe_allow_html=True)
    with f2: st.markdown('<div style="text-align:center;padding:1rem;background:#fff;border-radius:8px;border:1px solid #e0e0e0"><div style="font-size:2rem">⭐</div><div style="font-weight:700;color:#003580">Google Reviews</div><div style="font-size:.8rem;color:#6b6b6b">Photos & Ratings</div></div>',unsafe_allow_html=True)
    with f3: st.markdown('<div style="text-align:center;padding:1rem;background:#fff;border-radius:8px;border:1px solid #e0e0e0"><div style="font-size:2rem">🤖</div><div style="font-weight:700;color:#003580">AI Powered</div><div style="font-size:.8rem;color:#6b6b6b">GPT-4o-mini</div></div>',unsafe_allow_html=True)
    with f4: st.markdown('<div style="text-align:center;padding:1rem;background:#fff;border-radius:8px;border:1px solid #e0e0e0"><div style="font-size:2rem">🌤️</div><div style="font-weight:700;color:#003580">Live Weather</div><div style="font-size:.8rem;color:#6b6b6b">Google DeepMind</div></div>',unsafe_allow_html=True)
    st.stop()

sp=st.session_state.sp
oc,dc,ocity,dcity=sp["oc"],sp["dc"],sp["ocity"],sp["dcity"]
dep,ret,tvl,bud=sp["dep"],sp["ret"],sp["tvl"],sp["bud"]
fl_b,ht_b,fd_b,ac_b=sp["fl_b"],sp["ht_b"],sp["fd_b"],sp["ac_b"]
if not oc or not dc: st.error("Select airports from dropdown."); st.stop()

# Geocode + city hero photo
if "geo" not in st.session_state:
    st.session_state.geo=geocode_city(dcity,GKEY) if GKEY else (None,None)
dlat,dlng=st.session_state.geo
if "city_photo" not in st.session_state and GKEY:
    st.session_state.city_photo=gp_city_photo(dcity,GKEY)
if "gp_cache" not in st.session_state:
    st.session_state.gp_cache={}

# Google Places enrichment with caching
def enrich(name):
    if not GKEY or not name: return {}
    if name not in st.session_state.gp_cache:
        st.session_state.gp_cache[name]=gp_enrich(name,GKEY,dcity)
        time.sleep(0.1)
    return st.session_state.gp_cache[name]

# Build enriched data strings for itinerary/chat/budget (uses Google ratings + prices)
price_map={"PRICE_LEVEL_FREE":"Free","PRICE_LEVEL_INEXPENSIVE":"€","PRICE_LEVEL_MODERATE":"€€","PRICE_LEVEL_EXPENSIVE":"€€€","PRICE_LEVEL_VERY_EXPENSIVE":"€€€€"}

def enriched_restaurants_str():
    rests = st.session_state.get("rest_data",[])
    if not isinstance(rests, list): return ""
    parts = []
    for r in rests[:10]:
        name = r.get("name","")
        g = enrich(name) if GKEY else {}
        rating = g.get("g_rating","?")
        gpl = price_map.get(g.get("g_price_level",""), r.get("price_range","?"))
        parts.append(f"{name} (Google: {rating}★, {gpl})")
    return "Restaurants: " + ", ".join(parts) if parts else ""

def enriched_hotels_str():
    hotels = st.session_state.get("hotels_data",[])
    if not isinstance(hotels, list): return ""
    parts = []
    for h in hotels[:6]:
        name = h.get("name","")
        g = enrich(name) if GKEY else {}
        rating = g.get("g_rating","?")
        ppn = h.get("price_per_night",0)
        parts.append(f"{name} (Google: {rating}★, €{ppn}/night)")
    return "Hotels: " + ", ".join(parts) if parts else ""

def enriched_attractions_str():
    attrs = st.session_state.get("attr_data",[])
    if not isinstance(attrs, list): return ""
    parts = []
    for a in attrs[:10]:
        name = a.get("name","")
        g = enrich(name) if GKEY else {}
        rating = g.get("g_rating","?")
        free = "free" if a.get("free") else "paid"
        parts.append(f"{name} (Google: {rating}★, {free})")
    return "Attractions: " + ", ".join(parts) if parts else ""

def enriched_nightlife_str():
    nd = st.session_state.get("night_data",{})
    if not isinstance(nd, dict): return ""
    parts = []
    for b in nd.get("bars",[])[:5]:
        name = b.get("name","")
        g = enrich(name) if GKEY else {}
        rating = g.get("g_rating","?")
        parts.append(f"{name} ({rating}★)")
    return "Bars/Nightlife: " + ", ".join(parts) if parts else ""

def get_selections_str():
    parts = []
    sf = st.session_state.get("sel_flight")
    if sf:
        al = ", ".join(sf.get("out",{}).get("airlines",[])) if sf.get("out") else "?"
        parts.append(f"SELECTED FLIGHT: {al}, €{sf.get('price',0):,.0f}, {sf.get('cabin','ECONOMY')}")
    sh = st.session_state.get("sel_hotel")
    if sh:
        parts.append(f"SELECTED HOTEL: {sh.get('name','?')}, €{sh.get('per_night',0):,.0f}/night, €{sh.get('total',0):,.0f} total")
    return "\n".join(parts)

# ═══ LOAD ALL DATA AT ONCE ═══
def load_all():
    """Pre-load all API data so tabs don't block each other"""
    dht=ht_b/trip_days if trip_days>0 else ht_b
    dfb=fd_b/trip_days if trip_days>0 else fd_b
    # Flights
    if "flights_data" not in st.session_state and amadeus_token:
        raw=search_flights(amadeus_token,oc,dc,dep.strftime("%Y-%m-%d"),ret.strftime("%Y-%m-%d"),tvl)
        st.session_state.flights_data=[] if (isinstance(raw,dict) and "_error" in raw) else parse_flights(raw)
    # Hotels
    if "hotels_data" not in st.session_state and OAIKEY:
        st.session_state.hotels_data=ai_hotels(OAIKEY,dcity,accom,trip_days,dht)
    # Weather
    if "wx_data" not in st.session_state and GKEY and dlat:
        st.session_state.wx_data={"cur":gw_current(dlat,dlng,GKEY),"daily":gw_daily(dlat,dlng,GKEY,10),"hourly":gw_hourly(dlat,dlng,GKEY,48)}
    # Attractions
    if "attr_data" not in st.session_state and OAIKEY:
        st.session_state.attr_data=ai_attractions(OAIKEY,dcity,interests)
    # Restaurants
    if "rest_data" not in st.session_state and OAIKEY:
        st.session_state.rest_data=ai_restaurants(OAIKEY,dcity,food_prefs,dfb)
    # Nightlife
    if "night_data" not in st.session_state and OAIKEY:
        st.session_state.night_data=ai_nightlife(OAIKEY,dcity)

if "all_loaded" not in st.session_state:
    with st.spinner("🤖 Loading all travel data... flights, hotels, weather, attractions, restaurants, nightlife"):
        load_all()
        st.session_state.all_loaded = True

st.markdown("---")
# City hero photo with overlay text
cp=st.session_state.get("city_photo")
if cp:
    st.markdown(f"""<div style="position:relative;border-radius:8px;overflow:hidden;margin-bottom:1.5rem">
    <img src="{cp}" style="width:100%;height:250px;object-fit:cover;display:block">
    <div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,34,79,.85));padding:2rem 1.5rem 1.5rem">
    <div style="font-family:'Playfair Display',serif;font-size:2.2rem;font-weight:700;color:#fff">{ocity} → {dcity}</div>
    <div style="color:rgba(255,255,255,.85);font-size:.95rem">{dep.strftime('%b %d')} – {ret.strftime('%b %d, %Y')} · {trip_days} nights · {tvl} travelers</div>
    <span class="booking-yellow" style="margin-top:.5rem">€{bud:,} budget</span>
    </div></div>""", unsafe_allow_html=True)
else:
    st.markdown(f"## 🗺️ {ocity} → {dcity}")
    st.markdown(f"*{dep.strftime('%b %d')} – {ret.strftime('%b %d, %Y')} · {trip_days} nights · {tvl} travelers*")

# Budget metrics row
m1,m2,m3,m4=st.columns(4)
m1.metric("✈️ Flights",f"€{fl_b:,}"); m2.metric("🏨 Accom",f"€{ht_b:,}")
m3.metric("🍽️ Food",f"€{fd_b:,}"); m4.metric("🎭 Activities",f"€{ac_b:,}")

tabs=st.tabs(["✈️ Flights","🏨 Hotels","🌤️ Weather","🏛️ Attractions","🍽️ Restaurants","🌙 Nightlife","📋 Itinerary","💬 Chat","💰 Budget AI","🎵 TikTok","💱 Currency","🚇 Directions","🎒 Packing"])

# ═══ FLIGHTS ═══
with tabs[0]:
    if not amadeus_token: st.info("🔑 Add AMADEUS keys")
    else:
        flights=st.session_state.get("flights_data",[])
        if flights:
            st.success(f"**{len(flights)}** flights found")
            c1,c2=st.columns(2)
            with c1: sort=st.selectbox("Sort",["Price ↑","Price ↓"],key="fls")
            with c2: stops=st.selectbox("Stops",["Any","Direct","≤1"],key="flst")
            flt=flights.copy()
            if stops=="Direct": flt=[f for f in flt if f["out"] and f["out"]["stops"]==0]
            elif stops=="≤1": flt=[f for f in flt if f["out"] and f["out"]["stops"]<=1]
            if sort=="Price ↓": flt.sort(key=lambda x:x["price"],reverse=True)
            for i,f in enumerate(flt[:12]):
                o,r,pr,cab=f["out"],f["ret"],f["price"],f.get("cabin","ECONOMY")
                od=o["dep_time"][11:16] if o else "?"; oa=o["arr_time"][11:16] if o else "?"
                oal=", ".join(o["airlines"]) if o else "?"
                ost="Direct" if o and o["stops"]==0 else f"{o['stops']} stop" if o else ""
                rd=r["dep_time"][11:16] if r else "?"; ra=r["arr_time"][11:16] if r else "?"
                rst="Direct" if r and r["stops"]==0 else f"{r['stops']} stop" if r else ""
                ppp=pr/tvl; br=pr/fl_b if fl_b>0 else 1
                bc_,bl=("#27ae60","Great deal") if br<=0.6 else ("#f39c12","Good price") if br<=0.9 else ("#e74c3c","Near budget") if br<=1.2 else ("#999","Over budget")
                st.markdown(f"""<div class="fc"><div style="display:flex;justify-content:space-between;align-items:center">
                <div><div class="an">✈️ {oal} <span class="cb">{cab.replace('_',' ').title()}</span></div><div style="margin-top:.4rem">
                <div class="ri"><b>→</b> {od}–{oa} · {o['duration'] if o else ''} · {ost}</div>
                <div class="ri"><b>←</b> {rd}–{ra} · {r['duration'] if r else ''} · {rst}</div></div></div>
                <div style="text-align:right"><div class="pt">€{pr:,.0f}</div><div style="font-size:.8rem;color:#888">€{ppp:,.0f}/pers</div>
                <div style="font-size:.75rem;color:{bc_};font-weight:600">{bl}</div></div></div></div>""",unsafe_allow_html=True)
                if st.button(f"Select #{i+1}",key=f"sf_{i}"):
                    st.session_state.sel_flight=f; st.toast("Flight selected! ✅")
            if len(flt)>1:
                st.markdown("### 📊 Price Comparison")
                st.bar_chart(pd.DataFrame({"#":[f"#{i+1}" for i in range(min(len(flt),12))],"EUR":[f["price"] for f in flt[:12]]}).set_index("#"))
        else: st.warning("No flights found.")

# ═══ HOTELS (OpenAI + Google Places) ═══
with tabs[1]:
    if not OAIKEY: st.info("🔑 Add OPENAI_API_KEY")
    else:
        dht=ht_b/trip_days if trip_days>0 else ht_b
        hotels=st.session_state.get("hotels_data",[])
        if isinstance(hotels,str) and hotels.startswith("_ERR_"):
            st.error(hotels[6:])
        elif hotels:
            st.success(f"**{len(hotels)}** hotels recommended")
            st.markdown(f'<div class="mc" style="margin-bottom:1rem"><div class="mv">€{dht:,.0f}/night budget</div></div>',unsafe_allow_html=True)
            for i,h in enumerate(hotels):
                name=h.get("name",""); ppn=h.get("price_per_night",0); total=ppn*trip_days
                htype=h.get("type",""); nb=h.get("neighborhood",""); desc=h.get("description","")
                ib=ppn<=dht; bc_="#27ae60" if ib else "#e74c3c"; bl="✅ Within budget" if ib else "⚠️ Over budget"
                # Enrich with Google Places
                g=enrich(name)
                # Google price level
                gpl=g.get("g_price_level","")
                gpl_display=price_map.get(gpl,"")
                with st.expander(f"🏨 {name} {f'({gpl_display})' if gpl_display else ''}",expanded=(i<3)):
                    ic,info=st.columns([1,2])
                    with ic:
                        if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    with info:
                        st.markdown(f"**{name}**")
                        if g.get("g_rating"):
                            st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                        badges=f'<span class="cb">{htype.title()}</span>'
                        if gpl_display: badges+=f'<span class="cb" style="background:#fff3e0;color:#e65100">{gpl_display} Google Price</span>'
                        if nb: badges+=f'<span class="cb">📍 {nb}</span>'
                        st.markdown(badges,unsafe_allow_html=True)
                        st.markdown(f"_{desc}_")
                        if g.get("g_address"): st.caption(f"📍 {g['g_address']}")
                        c1,c2,c3=st.columns(3)
                        c1.metric("Est. price",f"~€{ppn:,.0f}/n"); c2.metric("Est. total",f"~€{total:,.0f}"); c3.metric("Budget",bl)
                        st.caption("💡 Prices are AI estimates. Check hotel website for real rates.")
                        if g.get("g_maps_url"): st.markdown(f"[📍 Google Maps]({g['g_maps_url']})")
                    # Reviews
                    if g.get("g_reviews"):
                        for rv in g["g_reviews"]:
                            st.markdown(f'> ⭐ {rv["rating"]}/5 — *"{rv["text"]}"* — **{rv["author"]}**')
                    if st.button(f"Select {name[:25]}",key=f"sh_{i}"):
                        st.session_state.sel_hotel={"name":name,"total":total,"per_night":ppn}; st.toast("Hotel selected! ✅")
        else: st.warning("Could not load hotels.")

# ═══ WEATHER ═══
with tabs[2]:
    if not GKEY or not dlat: st.info("🔑 Add GOOGLE_API_KEY")
    else:
        wx=st.session_state.get("wx_data",{}); cur=wx.get("cur")
        if cur:
            t=cur.get("temperature",{}).get("degrees",0); fl=cur.get("feelsLikeTemperature",{}).get("degrees",0)
            hm=cur.get("relativeHumidity",0); co=cur.get("weatherCondition",{}); ds=co.get("description",{}).get("text",""); wt=co.get("type","CLEAR")
            ws=cur.get("wind",{}).get("speed",{}).get("value",0)
            st.markdown(f'<div class="wc"><div style="font-size:3rem">{wx_emoji(wt)}</div><div class="wt">{t:.1f}°C</div><div style="opacity:.9">{ds}</div><div style="font-size:.9rem;opacity:.7;margin-top:.5rem">Feels {fl:.1f}°C · 💧 {hm}% · 💨 {ws} km/h</div></div>',unsafe_allow_html=True)
        daily=wx.get("daily")
        if daily:
            fd=daily.get("forecastDays",[])
            if fd:
                st.markdown("### 📅 10-Day Forecast")
                for rs in range(0,min(len(fd),10),5):
                    cols=st.columns(min(5,len(fd)-rs))
                    for idx,d in enumerate(fd[rs:rs+5]):
                        if idx>=len(cols): break
                        with cols[idx]:
                            dd=d.get("displayDate",{}); dc_=d.get("daytimeForecast",{}).get("weatherCondition",{})
                            mx=d.get("maxTemperature",{}).get("degrees","?"); mn=d.get("minTemperature",{}).get("degrees","?")
                            rp=d.get("daytimeForecast",{}).get("precipitation",{}).get("probability",{}).get("percent",0)
                            st.markdown(f'<div style="background:linear-gradient(135deg,#f0f2ff,#e8ecff);border-radius:12px;padding:.8rem;text-align:center"><div style="font-weight:600">{dd.get("month","")}/{dd.get("day","")}</div><div style="font-size:2rem">{wx_emoji(dc_.get("type","CLEAR"))}</div><div style="font-weight:700;color:#003580">{mx}°/{mn}°</div><div style="font-size:.7rem;color:#4a90d9">🌧 {rp}%</div></div>',unsafe_allow_html=True)
        hourly=wx.get("hourly")
        if hourly:
            hd=hourly.get("forecastHours",[])
            if hd:
                st.markdown("### 🌡️ 48h Temperature")
                st.line_chart(pd.DataFrame({"°C":[h.get("temperature",{}).get("degrees",0) for h in hd]},
                    index=[h.get("interval",{}).get("startTime","")[:16].replace("T"," ") for h in hd]))
        # Map
        if dlat and dlng:
            st.markdown("### 📍 Destination")
            st.map(pd.DataFrame({"lat":[dlat],"lon":[dlng]}),zoom=11)

# ═══ ATTRACTIONS (OpenAI + Google Places) ═══
with tabs[3]:
    if not OAIKEY: st.info("🔑 Add OPENAI_API_KEY")
    else:
        attrs=st.session_state.get("attr_data",[])
        if isinstance(attrs,str) and attrs.startswith("_ERR_"):
            st.error(attrs[6:])
        elif attrs:
            st.success(f"**{len(attrs)}** famous attractions")
            for a in attrs:
                name=a.get("name",""); atype=a.get("type",""); desc=a.get("description","")
                ms=a.get("must_see",False); hrs=a.get("estimated_hours",0); free=a.get("free",False)
                g=enrich(name)
                ms_badge='<span style="background:#ff6b6b;color:white;padding:.1rem .5rem;border-radius:10px;font-size:.75rem;font-weight:600">MUST SEE</span>' if ms else ""
                with st.expander(f"🏛️ {name} {' ⭐' if ms else ''}",expanded=ms):
                    ic,info=st.columns([1,2])
                    with ic:
                        if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    with info:
                        st.markdown(f"**{name}** {ms_badge}",unsafe_allow_html=True)
                        if g.get("g_rating"):
                            st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                        st.markdown(f'<span class="cb">{atype.title()}</span>{f" <span class=cb>⏱ {hrs}h</span>" if hrs else ""}{"<span class=cb style=background:#e8f5e9;color:#2e7d32>Free</span>" if free else ""}',unsafe_allow_html=True)
                        st.markdown(f"_{desc}_")
                        if g.get("g_address"): st.caption(f"📍 {g['g_address']}")
                        if g.get("g_maps_url"): st.markdown(f"[📍 Google Maps]({g['g_maps_url']})")
                    if g.get("g_reviews"):
                        for rv in g["g_reviews"][:1]:
                            st.markdown(f'> ⭐ {rv["rating"]}/5 — *"{rv["text"]}"*')
        else: st.warning("Could not load attractions.")

# ═══ RESTAURANTS (OpenAI + Google Places) ═══
with tabs[4]:
    if not OAIKEY: st.info("🔑 Add OPENAI_API_KEY")
    else:
        dfb=fd_b/trip_days if trip_days>0 else fd_b
        rests=st.session_state.get("rest_data",[])
        if isinstance(rests,str) and rests.startswith("_ERR_"):
            st.error(rests[6:])
        elif rests:
            st.success(f"**{len(rests)}** restaurants recommended")
            st.markdown(f'<div class="mc" style="margin-bottom:1rem"><div class="mv">€{dfb:,.0f}/day food budget</div></div>',unsafe_allow_html=True)
            cols=st.columns(2)
            for j,r in enumerate(rests):
                with cols[j%2]:
                    name=r.get("name",""); cuisine=r.get("cuisine",""); nb=r.get("neighborhood","")
                    desc=r.get("description",""); meal=r.get("meal","")
                    g=enrich(name)
                    # Use Google price level, fallback to OpenAI
                    gpl=g.get("g_price_level","")
                    price_map={"PRICE_LEVEL_FREE":"Free","PRICE_LEVEL_INEXPENSIVE":"€","PRICE_LEVEL_MODERATE":"€€","PRICE_LEVEL_EXPENSIVE":"€€€","PRICE_LEVEL_VERY_EXPENSIVE":"€€€€"}
                    pr_display=price_map.get(gpl, r.get("price_range",""))
                    if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    st.markdown(f'<div class="pc"><div style="font-weight:600;font-size:1.05rem">🍽️ {name}</div>',unsafe_allow_html=True)
                    if g.get("g_rating"):
                        st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                    st.markdown(f'<span class="cb">{cuisine}</span><span class="cb">{pr_display}</span>{f"<span class=cb>📍 {nb}</span>" if nb else ""}{f"<span class=cb>{meal}</span>" if meal else ""}',unsafe_allow_html=True)
                    st.markdown(f"_{desc}_")
                    if g.get("g_address"): st.caption(f"📍 {g['g_address']}")
                    if g.get("g_maps_url"): st.markdown(f"[Maps]({g['g_maps_url']})")
                    st.markdown("</div>",unsafe_allow_html=True)
        else: st.warning("Could not load restaurants.")

# ═══ NIGHTLIFE (OpenAI + Google Places) ═══
with tabs[5]:
    if not OAIKEY: st.info("🔑 Add OPENAI_API_KEY")
    else:
        nd=st.session_state.get("night_data",{})
        if isinstance(nd,str) and nd.startswith("_ERR_"):
            st.error(nd[6:]); nd={"bars":[],"cafes":[]}
        st.markdown("### 🍸 Bars & Nightlife")
        bars=nd.get("bars",[])
        if bars:
            cols=st.columns(2)
            for j,b in enumerate(bars):
                with cols[j%2]:
                    name=b.get("name",""); g=enrich(name)
                    if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    st.markdown(f'<div class="pc"><div style="font-weight:600">🍸 {name}</div>',unsafe_allow_html=True)
                    if g.get("g_rating"):
                        st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                    st.markdown(f'<span class="cb">{b.get("type","")}</span>{f"<span class=cb>📍 {b.get("neighborhood","")}</span>" if b.get("neighborhood") else ""}',unsafe_allow_html=True)
                    st.markdown(f'_{b.get("description","")}_')
                    if g.get("g_maps_url"): st.markdown(f"[Maps]({g['g_maps_url']})")
                    st.markdown("</div>",unsafe_allow_html=True)
        else: st.caption("No bars found.")
        st.markdown("### ☕ Cafes")
        cafes=nd.get("cafes",[])
        if cafes:
            cols=st.columns(3)
            for j,c in enumerate(cafes):
                with cols[j%3]:
                    name=c.get("name",""); g=enrich(name)
                    if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    st.markdown(f'<div class="pc"><div style="font-weight:600">☕ {name}</div>',unsafe_allow_html=True)
                    if g.get("g_rating"):
                        st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                    st.markdown(f'_{c.get("description","")}_')
                    st.markdown("</div>",unsafe_allow_html=True)
        else: st.caption("No cafes found.")

# ═══ ITINERARY ═══
with tabs[6]:
    st.markdown("### 📋 AI-Powered Itinerary")
    sf=st.session_state.get("sel_flight"); sh=st.session_state.get("sel_hotel")
    if sf: st.success(f"✈️ {', '.join(sf['out']['airlines']) if sf.get('out') else '?'} — €{sf['price']:,.0f}")
    else: st.info("Select a flight.")
    if sh: st.success(f"🏨 {sh['name']} — €{sh.get('total',0):,.0f} (€{sh.get('per_night',0):,.0f}/night)")
    else: st.info("Select a hotel.")
    fl_cost=sf["price"] if sf else fl_b; ht_cost=sh.get("total",ht_b) if sh else ht_b
    rem=bud-fl_cost-ht_cost; db=rem/trip_days if trip_days>0 else rem
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Budget",f"€{bud:,}"); m2.metric("Flights",f"€{fl_cost:,}")
    m3.metric("Accom",f"€{ht_cost:,}"); m4.metric("Remaining",f"€{rem:,}",delta=f"€{db:,.0f}/day")
    # Budget usage progress
    used_pct=(fl_cost+ht_cost)/bud if bud>0 else 0
    st.progress(min(used_pct,1.0),text=f"Budget used: {used_pct*100:.0f}%")

    if OAIKEY:
        c1,c2=st.columns([3,1])
        with c1: st.markdown("**🤖 Generate detailed day-by-day itinerary** using all collected data, Google ratings, and your selections.")
        with c2: gen=st.button("🧠 Generate",type="primary",use_container_width=True)
        if gen:
            wxs=None; wx=st.session_state.get("wx_data")
            if wx and wx.get("daily"):
                fd=wx["daily"].get("forecastDays",[])
                if fd: wxs=", ".join(f"{d.get('maxTemperature',{}).get('degrees','?')}°/{d.get('minTemperature',{}).get('degrees','?')}°" for d in fd[:5])
            # Build enriched context with Google data
            enriched_ctx = "\n".join(filter(None, [
                get_selections_str(),
                enriched_attractions_str(),
                enriched_restaurants_str(),
                enriched_hotels_str(),
                enriched_nightlife_str(),
                f"Weather: {wxs}" if wxs else ""
            ]))
            with st.spinner("🤖 Planning with your selections and Google data... (~20s)"):
                it=ai_itinerary(OAIKEY,dcity,dep,ret,trip_days,tvl,style,interests,food_prefs,db,
                    enriched_ctx=enriched_ctx)
            st.session_state["ai_itinerary"]=it
        if "ai_itinerary" in st.session_state:
            st.markdown("---"); st.markdown(st.session_state["ai_itinerary"])
            if st.button("🔄 Regenerate"): del st.session_state["ai_itinerary"]; st.rerun()
            st.download_button("📥 Download Itinerary",data=st.session_state["ai_itinerary"],
                file_name=f"itinerary_{dcity}.md",mime="text/markdown",use_container_width=True)
    else: st.warning("🔑 Add OPENAI_API_KEY")
    st.markdown("---")
    st.download_button("📥 Full Summary (JSON)",
        data=json.dumps({"trip":{"from":ocity,"to":dcity,"dep":str(dep),"ret":str(ret),"tvl":tvl,"bud":bud},
            "flight":{"price":sf["price"],"airlines":", ".join(sf["out"]["airlines"])} if sf and sf.get("out") else None,
            "hotel":sh,
            "attractions":[a.get("name") for a in (st.session_state.get("attr_data",[]) if isinstance(st.session_state.get("attr_data"),list) else [])],
            "restaurants":[r.get("name") for r in (st.session_state.get("rest_data",[]) if isinstance(st.session_state.get("rest_data"),list) else [])]
        },indent=2,default=str),
        file_name="voyageai.json",mime="application/json",use_container_width=True)

st.markdown("---")
# ═══ TRAVEL CHAT (Multi-turn LLM with trip context) ═══
with tabs[7]:
    st.markdown("### 💬 Ask VoyageAI")
    st.caption("Chat with an AI travel assistant that knows everything about your trip — flights, hotels, weather, restaurants, and itinerary.")
    if not OAIKEY:
        st.info("🔑 Add OPENAI_API_KEY")
    else:
        # Build enriched trip context with Google ratings and prices
        wxs = None
        wx = st.session_state.get("wx_data")
        if wx and wx.get("cur"):
            t = wx["cur"].get("temperature",{}).get("degrees","?")
            wxs = f"Current: {t}°C"
            if wx.get("daily"):
                fd = wx["daily"].get("forecastDays",[])
                if fd: wxs += ", Forecast: " + ", ".join(f"{d.get('maxTemperature',{}).get('degrees','?')}°/{d.get('minTemperature',{}).get('degrees','?')}°" for d in fd[:5])

        # Use enriched data with Google ratings/prices
        enriched = "\n".join(filter(None, [
            f"TRIP: {dcity}, {dep} to {ret}, {trip_days} days, {tvl} travelers, €{bud} budget, style: {style}",
            f"Interests: {', '.join(interests)}  |  Food: {', '.join(food_prefs)}",
            get_selections_str(),
            enriched_restaurants_str(),
            enriched_attractions_str(),
            enriched_hotels_str(),
            enriched_nightlife_str(),
            f"Weather: {wxs}" if wxs else "",
            f"ITINERARY:\n{st.session_state.get('ai_itinerary','')[:1500]}" if st.session_state.get("ai_itinerary") else ""
        ]))
        trip_ctx = enriched

        # Initialize chat history
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # Handle pending suggestion
        if "pending_chat" in st.session_state:
            pending = st.session_state.pop("pending_chat")
            st.session_state.chat_messages.append({"role":"user","content":pending})
            with st.spinner("Thinking..."):
                response = ai_chat(OAIKEY, st.session_state.chat_messages, trip_ctx)
            st.session_state.chat_messages.append({"role":"assistant","content":response})

        # Display chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Ask anything about your trip..."):
            st.session_state.chat_messages.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = ai_chat(OAIKEY, st.session_state.chat_messages, trip_ctx)
                st.markdown(response)
            st.session_state.chat_messages.append({"role":"assistant","content":response})

        # Quick question suggestions
        if not st.session_state.chat_messages:
            st.markdown("**💡 Try asking:**")
            suggestions = [
                f"What are the must-see places in {dcity}?",
                "How should I split my daily budget?",
                f"What's the best way to get around {dcity}?",
                "Any tips for saving money on food?",
                "What should I pack based on the weather?"
            ]
            cols = st.columns(2)
            for i, sug in enumerate(suggestions):
                with cols[i % 2]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state["pending_chat"] = sug
                        st.rerun()

        if st.session_state.chat_messages:
            if st.button("🗑️ Clear chat"):
                st.session_state.chat_messages = []
                st.rerun()

# ═══ BUDGET AI (Optimizer with structured output + charts) ═══
with tabs[8]:
    st.markdown("### 💰 AI Budget Optimizer")
    st.caption("AI analyzes your trip data and suggests specific ways to save money.")
    if not OAIKEY:
        st.info("🔑 Add OPENAI_API_KEY")
    else:
        if "budget_analysis" not in st.session_state:
            analyze = st.button("🧠 Analyze My Budget", type="primary", use_container_width=True)
            if analyze:
                # Build enriched context for budget analysis
                enriched_budget_ctx = "\n".join(filter(None, [
                    get_selections_str(),
                    enriched_restaurants_str(),
                    enriched_attractions_str(),
                    enriched_hotels_str()
                ]))
                with st.spinner("🤖 AI is analyzing your budget with Google data..."):
                    st.session_state.budget_analysis = ai_budget_optimizer(
                        OAIKEY, dcity, trip_days, tvl, bud, fl_b, ht_b, fd_b, ac_b,
                        sel_flight=st.session_state.get("sel_flight"),
                        sel_hotel=st.session_state.get("sel_hotel"),
                        enriched_ctx=enriched_budget_ctx
                    )
                    st.rerun()

        if "budget_analysis" in st.session_state:
            ba = st.session_state.budget_analysis
            if isinstance(ba, str) and ba.startswith("_ERR_"):
                st.error(ba[6:])
            elif isinstance(ba, dict):
                # Score and summary
                score = ba.get("score", 5)
                sc_color = "#27ae60" if score >= 7 else "#f39c12" if score >= 4 else "#e74c3c"
                sc_emoji = "🟢" if score >= 7 else "🟡" if score >= 4 else "🔴"
                st.markdown(f'<div class="mc"><div class="mv">{sc_emoji} Budget Score: {score}/10</div><div class="ml">{ba.get("summary","")}</div></div>', unsafe_allow_html=True)

                sav = ba.get("total_potential_savings", 0)
                if sav > 0:
                    st.metric("💡 Potential Savings", f"€{sav:,.0f}", delta=f"{sav/bud*100:.0f}% of budget")

                # Tips
                tips = ba.get("tips", [])
                if tips:
                    st.markdown("### 💡 Savings Tips")
                    for i, tip in enumerate(tips):
                        prio = tip.get("priority", "medium")
                        prio_emoji = "🔴" if prio == "high" else "🟡" if prio == "medium" else "🟢"
                        cat = tip.get("category", "general").title()
                        sav_tip = tip.get("potential_savings", 0)
                        with st.expander(f"{prio_emoji} {cat} — Save €{sav_tip:,.0f}", expanded=(i < 3)):
                            st.markdown(tip.get("tip", ""))

                    # Tips by category chart
                    cat_savings = {}
                    for tip in tips:
                        cat = tip.get("category", "general").title()
                        cat_savings[cat] = cat_savings.get(cat, 0) + tip.get("potential_savings", 0)
                    if cat_savings:
                        st.markdown("### 📊 Savings by Category")
                        st.bar_chart(pd.DataFrame({"Category": list(cat_savings.keys()), "Savings €": list(cat_savings.values())}).set_index("Category"))

                # Daily budget breakdown
                daily = ba.get("daily_budget_breakdown", {})
                if daily:
                    st.markdown("### 📅 Recommended Daily Spending")
                    d_cols = st.columns(len(daily))
                    for j, (k, v) in enumerate(daily.items()):
                        if j < len(d_cols):
                            d_cols[j].metric(k.title(), f"€{v:,.0f}")
                    total_daily = sum(daily.values())
                    if total_daily > 0:
                        st.progress(min(total_daily / (bud / trip_days if trip_days > 0 else bud), 1.0),
                                    text=f"Recommended €{total_daily:,.0f}/day vs budget €{bud/trip_days if trip_days>0 else bud:,.0f}/day")

                # Money saving alternatives
                alts = ba.get("money_saving_alternatives", [])
                if alts:
                    st.markdown("### 🔄 Cheaper Alternatives")
                    for alt in alts:
                        c1, c2, c3 = st.columns([3, 3, 1])
                        c1.markdown(f"~~{alt.get('original','')}~~")
                        c2.markdown(f"**→ {alt.get('alternative','')}**")
                        c3.markdown(f"**-€{alt.get('savings',0):,.0f}**")

            if st.button("🔄 Re-analyze"):
                del st.session_state["budget_analysis"]
                st.rerun()

# ═══ TIKTOK (AI-powered travel content discovery) ═══
with tabs[9]:
    st.markdown("### 🎵 TikTok Travel Guide")
    st.caption("Discover the best TikTok content to watch before your trip — trending creators, hidden gems, and food guides.")
    if not OAIKEY:
        st.info("🔑 Add OPENAI_API_KEY")
    else:
        if "tiktok_data" not in st.session_state:
            with st.spinner("🤖 Finding the best TikTok content..."):
                st.session_state.tiktok_data = ai_tiktok_recs(OAIKEY, dcity, interests)
        tk = st.session_state.tiktok_data
        if isinstance(tk, str) and tk.startswith("_ERR_"):
            st.error(tk[6:])
        elif isinstance(tk, dict):
            # Search queries with direct TikTok links
            queries = tk.get("search_queries", [])
            if queries:
                st.markdown("### 🔍 Search These on TikTok")
                cols = st.columns(2)
                for i, q in enumerate(queries):
                    with cols[i % 2]:
                        tiktok_url = f"https://www.tiktok.com/search?q={q.replace(' ', '%20')}"
                        st.markdown(f'<a href="{tiktok_url}" target="_blank" style="text-decoration:none"><div class="pc" style="cursor:pointer"><b>🔍 {q}</b><br><span style="font-size:.75rem;color:#888">Click to search on TikTok →</span></div></a>', unsafe_allow_html=True)

            # Creators
            creators = tk.get("creator_recommendations", [])
            if creators:
                st.markdown("### 👤 Creators to Follow")
                for cr in creators:
                    uname = cr.get("username", "")
                    profile_url = f"https://www.tiktok.com/{uname}" if uname.startswith("@") else f"https://www.tiktok.com/@{uname}"
                    st.markdown(f"""<div class="pc"><div style="display:flex;justify-content:space-between;align-items:center">
                    <div><div style="font-weight:600;font-size:1.05rem">🎵 {uname}</div>
                    <div style="font-size:.85rem;color:#666">{cr.get('description','')}</div>
                    <div style="font-size:.8rem;color:#003580;margin-top:.2rem">💡 {cr.get('why','')}</div></div>
                    <a href="{profile_url}" target="_blank" style="background:#003580;color:white;padding:.4rem 1rem;border-radius:20px;text-decoration:none;font-size:.85rem">Follow</a>
                    </div></div>""", unsafe_allow_html=True)

            # Trending topics
            topics = tk.get("trending_topics", [])
            if topics:
                st.markdown("### 🔥 Trending Topics")
                st.markdown(" · ".join(f'`#{t.replace(" ","")}`' for t in topics))

            # Video ideas
            videos = tk.get("video_ideas", [])
            if videos:
                st.markdown("### 🎬 Videos to Watch")
                cols = st.columns(2)
                for i, v in enumerate(videos):
                    with cols[i % 2]:
                        search_url = f"https://www.tiktok.com/search?q={v.get('search_term','').replace(' ','%20')}"
                        cat = v.get("category", "travel").title()
                        st.markdown(f"""<div class="pc"><div style="font-weight:600">🎬 {v.get('title','')}</div>
                        <span class="cb">{cat}</span>
                        <div style="margin-top:.3rem"><a href="{search_url}" target="_blank" style="color:#003580;font-size:.85rem">Search on TikTok →</a></div></div>""", unsafe_allow_html=True)

            if st.button("🔄 Refresh TikTok recs"):
                del st.session_state["tiktok_data"]
                st.rerun()

# ═══ CURRENCY CONVERTER ═══
with tabs[10]:
    st.markdown("### 💱 Currency Converter")
    if not OAIKEY:
        st.info("🔑 Add OPENAI_API_KEY")
    else:
        # Get local currency
        if "local_currency" not in st.session_state:
            with st.spinner("Detecting local currency..."):
                st.session_state.local_currency = get_currency_for_city(OAIKEY, dcity)
        lc = st.session_state.local_currency
        cur_code = lc.get("currency_code", "USD")
        cur_name = lc.get("currency_name", "US Dollar")
        cur_symbol = lc.get("symbol", "$")
        st.markdown(f'<div class="mc"><div class="mv">{cur_symbol} {cur_name} ({cur_code})</div><div class="ml">Local currency in {dcity}</div></div>', unsafe_allow_html=True)

        # Get rates
        if "exchange_rates" not in st.session_state:
            st.session_state.exchange_rates = get_exchange_rates("EUR")
        rates = st.session_state.exchange_rates
        if rates and rates.get("rates"):
            st.caption(f"Rates as of {rates.get('date','')}")
            # Converter
            c1, c2 = st.columns(2)
            with c1:
                amount = st.number_input("Amount in EUR", min_value=0.0, value=100.0, step=10.0)
            with c2:
                target = st.selectbox("Convert to", [cur_code] + sorted([k for k in rates["rates"].keys() if k != cur_code]), key="conv_cur")
            rate = rates["rates"].get(target, 1)
            converted = amount * rate
            st.markdown(f'<div class="mc"><div class="mv">€{amount:,.2f} = {cur_symbol if target==cur_code else ""}{converted:,.2f} {target}</div><div class="ml">Rate: 1 EUR = {rate:.4f} {target}</div></div>', unsafe_allow_html=True)

            # Quick reference table
            st.markdown("### 💡 Quick Reference")
            quick = [1, 5, 10, 20, 50, 100, 200, 500]
            qdf = pd.DataFrame({"EUR": [f"€{v}" for v in quick], target: [f"{v*rate:,.2f}" for v in quick]})
            st.dataframe(qdf, hide_index=True, use_container_width=True)

            # Common currencies
            st.markdown("### 🌍 Major Rates")
            major = ["USD","GBP","JPY","CHF","AUD","CAD"]
            mcols = st.columns(3)
            for i, mc in enumerate(major):
                if mc in rates["rates"]:
                    with mcols[i % 3]:
                        st.metric(mc, f"{rates['rates'][mc]:.4f}", delta=None)
        else:
            st.warning("Could not load exchange rates.")

# ═══ DIRECTIONS ═══
with tabs[11]:
    st.markdown("### 🚇 Getting Around")
    st.caption(f"Calculate travel time and see the route on Google Maps")
    if not GKEY:
        st.info("🔑 Add GOOGLE_API_KEY")
    else:
        # Build list of known places
        places = []
        if isinstance(st.session_state.get("hotels_data"), list):
            places += [f"🏨 {h.get('name','')}" for h in st.session_state["hotels_data"] if h.get("name")]
        if isinstance(st.session_state.get("attr_data"), list):
            places += [f"🏛️ {a.get('name','')}" for a in st.session_state["attr_data"] if a.get("name")]
        if isinstance(st.session_state.get("rest_data"), list):
            places += [f"🍽️ {r.get('name','')}" for r in st.session_state["rest_data"] if r.get("name")]
        nd = st.session_state.get("night_data",{})
        if isinstance(nd, dict):
            places += [f"🍸 {b.get('name','')}" for b in nd.get("bars",[]) if b.get("name")]

        # Input mode: dropdown or free text
        input_mode = st.radio("Input mode", ["📋 Choose from trip places", "✏️ Type any address"], horizontal=True, key="dir_input_mode")

        c1, c2 = st.columns(2)
        if input_mode == "📋 Choose from trip places" and places:
            with c1:
                orig_sel = st.selectbox("📍 From", places, key="dir_from")
                orig_dir = orig_sel.split(" ", 1)[1] if " " in orig_sel else orig_sel
            with c2:
                dest_sel = st.selectbox("📍 To", places, index=min(1, len(places)-1), key="dir_to")
                dest_dir = dest_sel.split(" ", 1)[1] if " " in dest_sel else dest_sel
        else:
            with c1:
                orig_dir = st.text_input("📍 From", placeholder=f"e.g. Colosseum, {dcity}", key="dir_from_txt")
            with c2:
                dest_dir = st.text_input("📍 To", placeholder=f"e.g. Central Station, {dcity}", key="dir_to_txt")

        mode = st.radio("🚗 Mode", ["transit", "walking", "driving", "bicycling"], horizontal=True)

        if st.button("🔍 Get Directions", type="primary"):
            if orig_dir and dest_dir:
                st.session_state.dir_origin = f"{orig_dir}, {dcity}"
                st.session_state.dir_dest = f"{dest_dir}, {dcity}"
                st.session_state.dir_mode = mode
                with st.spinner("Calculating route..."):
                    dirs = get_directions(st.session_state.dir_origin, st.session_state.dir_dest, GKEY, mode)
                if dirs:
                    st.session_state.last_directions = dirs
                else:
                    st.warning("Could not find route. Try different places or mode.")

        if "last_directions" in st.session_state:
            d = st.session_state.last_directions
            dc1, dc2, dc3 = st.columns(3)
            dc1.metric("⏱ Duration", d["duration"])
            dc2.metric("📏 Distance", d["distance"])
            dc3.metric("🚗 Mode", st.session_state.get("dir_mode","transit").title())

            # Embedded Google Maps with directions
            origin_enc = st.session_state.get("dir_origin","").replace(" ","+")
            dest_enc = st.session_state.get("dir_dest","").replace(" ","+")
            map_mode = st.session_state.get("dir_mode","transit")
            maps_embed_url = f"https://www.google.com/maps/embed/v1/directions?key={GKEY}&origin={origin_enc}&destination={dest_enc}&mode={map_mode}"
            st.markdown(f'<iframe src="{maps_embed_url}" width="100%" height="450" style="border:0;border-radius:14px" allowfullscreen loading="lazy"></iframe>', unsafe_allow_html=True)

            # Also show a link to open in full Google Maps
            gmaps_url = f"https://www.google.com/maps/dir/{origin_enc}/{dest_enc}/@{dlat},{dlng},13z/data=!4m2!4m1!3e{'1' if map_mode=='transit' else '2' if map_mode=='walking' else '0'}"
            st.markdown(f"[🗺️ Open in Google Maps]({gmaps_url})")

            # Steps
            steps = d.get("steps", [])
            if steps:
                with st.expander("📋 Detailed Route Steps", expanded=False):
                    for i, step in enumerate(steps):
                        instr = step.get("instruction","").replace("<b>","**").replace("</b>","**").replace("<div>",". ").replace("</div>","")
                        dur = step.get("duration","")
                        st.markdown(f"**{i+1}.** {instr} *({dur})*")

# ═══ PACKING LIST ═══
with tabs[12]:
    st.markdown("### 🎒 Smart Packing List")
    st.caption("AI-generated packing list based on weather forecast and your planned activities.")
    if not OAIKEY:
        st.info("🔑 Add OPENAI_API_KEY")
    else:
        if "packing_data" not in st.session_state:
            gen_pack = st.button("🎒 Generate Packing List", type="primary", use_container_width=True)
            if gen_pack:
                # Build weather summary
                wxs = None
                wx = st.session_state.get("wx_data", {})
                if wx.get("daily"):
                    fd = wx["daily"].get("forecastDays", [])
                    if fd:
                        temps = [f"{d.get('maxTemperature',{}).get('degrees','?')}°/{d.get('minTemperature',{}).get('degrees','?')}°" for d in fd[:7]]
                        wxs = f"Daily temps: {', '.join(temps)}"
                        rain_days = sum(1 for d in fd[:7] if d.get("daytimeForecast",{}).get("precipitation",{}).get("probability",{}).get("percent",0) > 30)
                        if rain_days: wxs += f". {rain_days} days with rain expected"
                with st.spinner("🤖 Creating your packing list..."):
                    st.session_state.packing_data = ai_packing_list(OAIKEY, dcity, trip_days, wxs, interests, style)
                st.rerun()

        if "packing_data" in st.session_state:
            pk = st.session_state.packing_data
            if isinstance(pk, str) and pk.startswith("_ERR_"):
                st.error(pk[6:])
            elif isinstance(pk, dict):
                # Weather advisory
                adv = pk.get("weather_advisory", "")
                if adv:
                    st.markdown(f'<div class="wc" style="background:linear-gradient(135deg,#667eea,#764ba2)"><div style="font-size:1.1rem">🌤️ {adv}</div></div>', unsafe_allow_html=True)

                # Sections
                sections = [
                    ("📋 Essentials", "essentials"),
                    ("👕 Clothing", "clothing"),
                    ("📱 Tech", "tech"),
                    ("💊 Health & Safety", "health"),
                    ("📄 Documents", "documents")
                ]
                for title, key in sections:
                    items = pk.get(key, [])
                    if items:
                        with st.expander(f"{title} ({len(items)} items)", expanded=(key in ["essentials","clothing"])):
                            for item in items:
                                name = item.get("item", "")
                                reason = item.get("reason", "")
                                prio = item.get("priority", "")
                                qty = item.get("quantity", "")
                                prio_icon = "🔴" if prio == "must" else "🟡" if prio == "recommended" else "⚪"
                                qty_str = f" ×{qty}" if qty else ""
                                st.markdown(f"{prio_icon} **{name}{qty_str}** — _{reason}_")

                # Tips
                tips = pk.get("tips", [])
                if tips:
                    st.markdown("### 💡 Packing Tips")
                    for tip in tips:
                        st.markdown(f"• {tip}")

            if st.button("🔄 Regenerate packing list"):
                del st.session_state["packing_data"]
                st.rerun()

st.markdown("---")
st.markdown("""<div style="text-align:center;padding:1.5rem;background:#003580;border-radius:8px;margin-top:1rem">
<div style="font-family:'Playfair Display',serif;font-size:1.2rem;color:#fff;margin-bottom:.3rem">✈️ VoyageAI</div>
<div style="color:rgba(255,255,255,.6);font-size:.8rem">Powered by Amadeus · Google Weather · Google Places · Google Directions · Frankfurter · OpenAI</div>
<div style="margin-top:.3rem;font-size:.7rem;color:rgba(255,255,255,.4)">Built by Francesco Polimeni — PDAI 2026</div>
</div>""", unsafe_allow_html=True)
