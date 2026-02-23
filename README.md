# ✈️ VoyageAI — AI-Powered Travel Planner

Streamlit prototype for an AI-powered travel agency that aggregates real data from 4 APIs.

## Features

| Tab | Data Source | What it does |
|-----|-----------|--------------|
| ✈️ Flights | Amadeus Flight Offers | Search, compare & select real flights (400+ airlines) |
| 🏨 Hotels | Amadeus Hotel Search | Browse hotels with pricing, room types, budget fit |
| 🌤️ Weather | Google Weather API | Current + 10-day forecast + hourly trend (DeepMind AI) |
| 🏛️ Attractions | OpenTripMap | Top-rated landmarks, museums, heritage sites |
| 🍽️ Restaurants | Foursquare | Restaurants by cuisine, with photos & tips |
| 🌙 Nightlife | Foursquare | Bars, cafes, shopping |
| 📋 Itinerary | All combined | AI-generated daily plan with budget tracking |

## Quick Start

```bash
git clone <your-repo-url>
cd travel_app
pip install -r requirements.txt
```

### Configure API Keys (choose one method):

**Option A — `.streamlit/secrets.toml` (recommended, never committed to git):**
```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit with your keys
```

**Option B — Environment variables:**
```bash
export AMADEUS_CLIENT_ID=xxx
export AMADEUS_CLIENT_SECRET=xxx
export GOOGLE_API_KEY=xxx
export FOURSQUARE_API_KEY=xxx
export OPENTRIPMAP_API_KEY=xxx
```

**Option C — Enter in sidebar** (for quick testing)

Then run:
```bash
streamlit run app.py
```

## API Keys (all free)

| API | URL | Free Tier |
|-----|-----|-----------|
| Amadeus | [developers.amadeus.com](https://developers.amadeus.com/) | 2,000 searches/month |
| Google Maps | [console.cloud.google.com](https://console.cloud.google.com/) | $200 credit/month |
| Foursquare | [developer.foursquare.com](https://developer.foursquare.com/) | Free tier |
| OpenTripMap | [opentripmap.io](https://opentripmap.io/) | Free |

**Google setup:** Enable both **Weather API** and **Geocoding API** in Cloud Console.

## Project Structure

```
travel_app/
├── app.py                          # Main Streamlit app
├── api_functions.py                # All API integrations
├── requirements.txt
├── .gitignore                      # Protects secrets
├── .env.example                    # Template for env vars
├── .streamlit/
│   └── secrets.toml.example        # Template for Streamlit secrets
└── README.md
```

## Key Design Decisions

- **API keys protected**: `.env` and `secrets.toml` are gitignored. Three fallback methods.
- **Session state caching**: Flight/hotel/weather results cached in `st.session_state` — selecting a flight doesn't reset other tabs.
- **Live airport search**: Type 2+ characters → Amadeus autocomplete → select from dropdown.
- **Top attractions**: OpenTripMap `rate=3h` parameter filters for heritage-rated, top-tier landmarks.
- **Foursquare queries**: Specific search terms per cuisine ("Italian restaurant", "sushi", etc.) instead of generic "restaurant".

## Streamlit Widgets (16+)

`st.tabs` · `st.expander` · `st.select_slider` · `st.multiselect` · `st.radio` (horizontal) · `st.slider` · `st.number_input` · `st.date_input` · `st.selectbox` · `st.text_input` · `st.columns` · `st.metric` · `st.bar_chart` · `st.line_chart` · `st.download_button` · `st.toast` · `st.spinner` · `st.image` · Custom CSS

---
*Built for PDAI Assignment 1*
