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
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Source+Sans+Pro:wght@300;400;600&display=swap');
.main .block-container{padding-top:2rem;max-width:1200px}
h1,h2,h3{font-family:'Playfair Display',serif!important}
.hero{font-family:'Playfair Display',serif;font-size:3rem;font-weight:700;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;margin-bottom:0}
.sub{text-align:center;color:#666;margin-bottom:2rem}
.fc{background:linear-gradient(135deg,#fff,#f8f9ff);border:1px solid #e0e4f0;border-radius:16px;padding:1.5rem;margin-bottom:1rem;box-shadow:0 4px 15px rgba(0,0,0,.05)}
.fc:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(0,0,0,.1)}
.pt{font-family:'Playfair Display',serif;font-size:1.8rem;font-weight:700;color:#0f3460}
.an{font-weight:600;font-size:1.1rem;color:#333}
.ri{color:#555;font-size:.95rem}
.wc{background:linear-gradient(135deg,#667eea,#764ba2);border-radius:16px;padding:1.5rem;color:#fff;text-align:center;margin-bottom:1rem}
.wt{font-family:'Playfair Display',serif;font-size:2.5rem;font-weight:700}
.pc{background:#fff;border:1px solid #eee;border-radius:12px;padding:1rem;margin-bottom:.8rem;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.cb{display:inline-block;background:#eef1ff;color:#0f3460;padding:.15rem .6rem;border-radius:20px;font-size:.75rem;font-weight:600;margin-right:.3rem;margin-bottom:.2rem}
.mc{background:linear-gradient(135deg,#f8f9ff,#eef1ff);border-radius:12px;padding:1rem;text-align:center;border:1px solid #e0e4f0}
.mv{font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;color:#0f3460}
.ml{font-size:.85rem;color:#888}
.stars{color:#f5a623;font-size:1rem}
div[data-testid="stSidebar"]{background:linear-gradient(180deg,#1a1a2e,#16213e)}
div[data-testid="stSidebar"] p,div[data-testid="stSidebar"] label,div[data-testid="stSidebar"] h1,div[data-testid="stSidebar"] h2,div[data-testid="stSidebar"] h3{color:#fff!important}
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
        q=st.text_input(label,key=f"{sk}_q",placeholder="Type city...")
        if amadeus_token and q and len(q)>=2:
            ck=f"_ap_{sk}_{q}"
            if ck not in st.session_state: st.session_state[ck]=search_airports(q,amadeus_token)
            res=st.session_state[ck]
            if res:
                sel=st.selectbox("Select",list(res.keys()),key=f"{sk}_s",label_visibility="collapsed")
                return res[sel]["code"],res[sel]["city"]
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
        for k in ["flights_data","hotels_data","wx_data","attr_data","rest_data","night_data","ai_itinerary","geo","city_photo","gp_cache"]:
            st.session_state.pop(k,None)
        st.session_state.search_done=True
        st.session_state.sp={"oc":orig_code,"dc":dest_code,"ocity":orig_city,"dcity":dest_city,
            "dep":dep_date,"ret":ret_date,"tvl":travelers,"bud":budget,
            "fl_b":fl_b,"ht_b":ht_b,"fd_b":fd_b,"ac_b":ac_b}

# ═══ MAIN ═══
st.markdown('<p class="hero">✈️ VoyageAI</p>',unsafe_allow_html=True)
st.markdown('<p class="sub">AI-Powered Travel Planner · Real Flights · Google Photos & Reviews · AI Recommendations</p>',unsafe_allow_html=True)

if not st.session_state.get("search_done"):
    st.info("👈 Set up your trip and click **Plan My Trip!**"); st.stop()

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

st.markdown("---")
# City hero photo
cp=st.session_state.get("city_photo")
if cp: st.image(cp,use_container_width=True)
st.markdown(f"## 🗺️ {ocity} → {dcity}")
st.markdown(f"*{dep.strftime('%b %d')} – {ret.strftime('%b %d, %Y')} · {trip_days} nights · {tvl} travelers*")

# Budget metrics row
m1,m2,m3,m4=st.columns(4)
m1.metric("✈️ Flights",f"€{fl_b:,}"); m2.metric("🏨 Accom",f"€{ht_b:,}")
m3.metric("🍽️ Food",f"€{fd_b:,}"); m4.metric("🎭 Activities",f"€{ac_b:,}")

tabs=st.tabs(["✈️ Flights","🏨 Hotels","🌤️ Weather","🏛️ Attractions","🍽️ Restaurants","🌙 Nightlife","📋 Itinerary"])

# ═══ FLIGHTS ═══
with tabs[0]:
    if not amadeus_token: st.info("🔑 Add AMADEUS keys")
    else:
        if "flights_data" not in st.session_state:
            with st.spinner("Searching flights..."):
                raw=search_flights(amadeus_token,oc,dc,dep.strftime("%Y-%m-%d"),ret.strftime("%Y-%m-%d"),tvl)
                st.session_state.flights_data=[] if (isinstance(raw,dict) and "_error" in raw) else parse_flights(raw)
                if isinstance(raw,dict) and "_error" in raw: st.warning(raw["_error"])
        flights=st.session_state.flights_data
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
        if "hotels_data" not in st.session_state:
            with st.spinner("🤖 AI finding hotels..."):
                st.session_state.hotels_data=ai_hotels(OAIKEY,dcity,accom,trip_days,dht)
        hotels=st.session_state.hotels_data
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
                with st.expander(f"🏨 {name} — €{ppn:,.0f}/night",expanded=(i<3)):
                    ic,info=st.columns([1,2])
                    with ic:
                        if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    with info:
                        st.markdown(f"**{name}**")
                        if g.get("g_rating"):
                            st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                        st.markdown(f'<span class="cb">{htype.title()}</span>{f" <span class=cb>📍 {nb}</span>" if nb else ""}',unsafe_allow_html=True)
                        st.markdown(f"_{desc}_")
                        if g.get("g_address"): st.caption(f"📍 {g['g_address']}")
                        c1,c2,c3=st.columns(3)
                        c1.metric("Per night",f"€{ppn:,.0f}"); c2.metric("Total",f"€{total:,.0f}"); c3.metric("Budget",bl)
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
        if "wx_data" not in st.session_state:
            with st.spinner("Fetching weather..."):
                st.session_state.wx_data={"cur":gw_current(dlat,dlng,GKEY),"daily":gw_daily(dlat,dlng,GKEY,10),"hourly":gw_hourly(dlat,dlng,GKEY,48)}
        wx=st.session_state.wx_data; cur=wx.get("cur")
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
                            st.markdown(f'<div style="background:linear-gradient(135deg,#f0f2ff,#e8ecff);border-radius:12px;padding:.8rem;text-align:center"><div style="font-weight:600">{dd.get("month","")}/{dd.get("day","")}</div><div style="font-size:2rem">{wx_emoji(dc_.get("type","CLEAR"))}</div><div style="font-weight:700;color:#0f3460">{mx}°/{mn}°</div><div style="font-size:.7rem;color:#4a90d9">🌧 {rp}%</div></div>',unsafe_allow_html=True)
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
        if "attr_data" not in st.session_state:
            with st.spinner("🤖 AI finding famous attractions..."):
                st.session_state.attr_data=ai_attractions(OAIKEY,dcity,interests)
        attrs=st.session_state.attr_data
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
        if "rest_data" not in st.session_state:
            with st.spinner("🤖 AI finding restaurants..."):
                st.session_state.rest_data=ai_restaurants(OAIKEY,dcity,food_prefs,dfb)
        rests=st.session_state.rest_data
        if isinstance(rests,str) and rests.startswith("_ERR_"):
            st.error(rests[6:])
        elif rests:
            st.success(f"**{len(rests)}** restaurants recommended")
            st.markdown(f'<div class="mc" style="margin-bottom:1rem"><div class="mv">€{dfb:,.0f}/day food budget</div></div>',unsafe_allow_html=True)
            cols=st.columns(2)
            for j,r in enumerate(rests):
                with cols[j%2]:
                    name=r.get("name",""); cuisine=r.get("cuisine",""); nb=r.get("neighborhood","")
                    pr=r.get("price_range",""); desc=r.get("description",""); meal=r.get("meal","")
                    g=enrich(name)
                    if g.get("g_photo"): st.image(g["g_photo"],use_container_width=True)
                    st.markdown(f'<div class="pc"><div style="font-weight:600;font-size:1.05rem">🍽️ {name}</div>',unsafe_allow_html=True)
                    if g.get("g_rating"):
                        st.markdown(stars_html(g["g_rating"],g.get("g_reviews_count")),unsafe_allow_html=True)
                    st.markdown(f'<span class="cb">{cuisine}</span><span class="cb">{pr}</span>{f"<span class=cb>📍 {nb}</span>" if nb else ""}{f"<span class=cb>{meal}</span>" if meal else ""}',unsafe_allow_html=True)
                    st.markdown(f"_{desc}_")
                    if g.get("g_address"): st.caption(f"📍 {g['g_address']}")
                    if g.get("g_maps_url"): st.markdown(f"[Maps]({g['g_maps_url']})")
                    st.markdown("</div>",unsafe_allow_html=True)
        else: st.warning("Could not load restaurants.")

# ═══ NIGHTLIFE (OpenAI + Google Places) ═══
with tabs[5]:
    if not OAIKEY: st.info("🔑 Add OPENAI_API_KEY")
    else:
        if "night_data" not in st.session_state:
            with st.spinner("🤖 AI finding nightlife..."):
                st.session_state.night_data=ai_nightlife(OAIKEY,dcity)
        nd=st.session_state.night_data
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
        with c1: st.markdown("**🤖 Generate detailed day-by-day itinerary** using all collected data.")
        with c2: gen=st.button("🧠 Generate",type="primary",use_container_width=True)
        if gen:
            wxs=None; wx=st.session_state.get("wx_data")
            if wx and wx.get("daily"):
                fd=wx["daily"].get("forecastDays",[])
                if fd: wxs=", ".join(f"{d.get('maxTemperature',{}).get('degrees','?')}°/{d.get('minTemperature',{}).get('degrees','?')}°" for d in fd[:5])
            with st.spinner("🤖 Planning... (~20s)"):
                it=ai_itinerary(OAIKEY,dcity,dep,ret,trip_days,tvl,style,interests,food_prefs,db,
                    st.session_state.get("attr_data",[]) if isinstance(st.session_state.get("attr_data"),list) else [],
                    st.session_state.get("rest_data",[]) if isinstance(st.session_state.get("rest_data"),list) else [],
                    st.session_state.get("hotels_data",[]) if isinstance(st.session_state.get("hotels_data"),list) else [],wxs)
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
st.markdown('<div style="text-align:center;color:#aaa;font-size:.8rem;padding:1rem">✈️ VoyageAI — 4 APIs: Amadeus · Google Weather · Google Places · OpenAI</div>',unsafe_allow_html=True)
