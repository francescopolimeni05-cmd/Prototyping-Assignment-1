"""
Agentic trip planner — OpenAI function-calling loop.

Exposes a small set of tools backed by the existing VoyageAI API layer
(amadeus, google places, openai content generation). The LLM decides which
to call in which order given a freeform user goal.

We intentionally keep the loop short (max_steps=8) to bound latency/cost for
a prototype. Each step is recorded for the frontend to display a progress
trace.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from .. import config
from ..schemas import (
    AgentPlanRequest,
    AgentPlanResponse,
    AgentStep,
    DayBlock,
    DayPlan,
    StructuredItinerary,
)
from .openai_client import client as openai_client
from .itinerary_service import generate_structured
from ..schemas import ItineraryGenerateRequest

# We reuse the A2 api_functions directly — they live one level up in the repo.
# This import works because backend/ is a sibling of api_functions.py.
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import api_functions as af  # type: ignore


# ── Tool implementations ───────────────────────────────────────────────────

def _tool_search_flights(origin_iata: str, destination_iata: str, depart: str, ret: str, adults: int = 1) -> dict:
    # Best effort: if auth fails, pass a bad token — search_flights has a
    # built-in mock fallback that activates when Amadeus is unreachable.
    tok = af.get_amadeus_token(config.AMADEUS_CLIENT_ID, config.AMADEUS_CLIENT_SECRET) or ""
    raw = af.search_flights(tok, origin_iata, destination_iata, depart, ret, adults)
    flights = af.parse_flights(raw) if not (isinstance(raw, dict) and "_error" in raw) else []
    return {
        "count": len(flights),
        "cheapest": flights[0] if flights else None,
        "source": "mock" if isinstance(raw, dict) and raw.get("_mock") else "amadeus",
    }


def _tool_search_hotels(city: str, nights: int, budget_per_night: float) -> dict:
    return {"hotels": af.ai_hotels(config.OPENAI_API_KEY, city, "hotel", nights, budget_per_night)}


def _tool_search_restaurants(city: str, food_prefs: list[str], daily_budget: float) -> dict:
    return {"restaurants": af.ai_restaurants(config.OPENAI_API_KEY, city, food_prefs, daily_budget)}


def _tool_search_attractions(city: str, interests: list[str]) -> dict:
    return {"attractions": af.ai_attractions(config.OPENAI_API_KEY, city, interests)}


def _tool_get_weather(city: str) -> dict:
    lat, lng = af.geocode_city(city, config.GOOGLE_API_KEY)
    if not lat:
        return {"error": f"Could not geocode {city}"}
    daily = af.gw_daily(lat, lng, config.GOOGLE_API_KEY, 10) or {}
    fd = daily.get("forecastDays", [])[:5]
    summary = ", ".join(
        f"{d.get('maxTemperature',{}).get('degrees','?')}°/{d.get('minTemperature',{}).get('degrees','?')}°"
        for d in fd
    )
    return {"summary": summary, "days": len(fd)}


def _tool_compose_itinerary(
    destination: str,
    depart: str,
    ret: str,
    days: int,
    travelers: int,
    style: str,
    interests: list[str],
    food_prefs: list[str],
    daily_budget: float,
    enriched_context: str = "",
    weather_summary: str = "",
) -> dict:
    req = ItineraryGenerateRequest(
        destination=destination,
        depart_date=depart,
        return_date=ret,
        days=days,
        travelers=travelers,
        style=style,
        interests=interests,
        food_prefs=food_prefs,
        daily_budget=daily_budget,
        enriched_context=enriched_context,
        weather_summary=weather_summary,
    )
    plan = generate_structured(req)
    return plan.model_dump()


TOOL_IMPL: dict[str, Callable[..., dict]] = {
    "search_flights": _tool_search_flights,
    "search_hotels": _tool_search_hotels,
    "search_restaurants": _tool_search_restaurants,
    "search_attractions": _tool_search_attractions,
    "get_weather": _tool_get_weather,
    "compose_itinerary": _tool_compose_itinerary,
}


# ── OpenAI tool schemas ───────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search round-trip flights between two IATA codes. Returns the cheapest option.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_iata": {"type": "string", "description": "Origin IATA code, e.g. 'BCN'"},
                    "destination_iata": {"type": "string", "description": "Destination IATA code, e.g. 'NRT'"},
                    "depart": {"type": "string", "description": "YYYY-MM-DD"},
                    "ret": {"type": "string", "description": "YYYY-MM-DD"},
                    "adults": {"type": "integer", "default": 1},
                },
                "required": ["origin_iata", "destination_iata", "depart", "ret"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Find hotels in a city for N nights under a nightly budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "nights": {"type": "integer"},
                    "budget_per_night": {"type": "number"},
                },
                "required": ["city", "nights", "budget_per_night"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": "Find restaurants in a city given food preferences and a daily food budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "food_prefs": {"type": "array", "items": {"type": "string"}},
                    "daily_budget": {"type": "number"},
                },
                "required": ["city", "food_prefs", "daily_budget"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "List famous attractions in a city filtered by interests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "interests": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["city", "interests"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get a 5-day weather summary for a city.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compose_itinerary",
            "description": "Compose the final multi-day structured itinerary. Call this LAST once you have gathered flights/hotels/restaurants/attractions/weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "depart": {"type": "string"},
                    "ret": {"type": "string"},
                    "days": {"type": "integer"},
                    "travelers": {"type": "integer"},
                    "style": {"type": "string"},
                    "interests": {"type": "array", "items": {"type": "string"}},
                    "food_prefs": {"type": "array", "items": {"type": "string"}},
                    "daily_budget": {"type": "number"},
                    "enriched_context": {"type": "string"},
                    "weather_summary": {"type": "string"},
                },
                "required": [
                    "destination", "depart", "ret", "days", "travelers",
                    "style", "interests", "food_prefs", "daily_budget",
                ],
            },
        },
    },
]


AGENT_SYSTEM = """You are VoyageAI's autonomous trip planner.

Your job is to read the user's freeform goal, call a FEW tools to gather
context, then call `compose_itinerary` EXACTLY ONCE at the end to produce
the final plan. You MUST finish by calling `compose_itinerary` — the UI
shows nothing if you don't.

STRICT BUDGET: at most 5 tool calls before `compose_itinerary`. Then one
call to `compose_itinerary`. That's it.

Suggested order:
  1. `get_weather` for the destination city
  2. `search_hotels` or `search_attractions` (pick one or two — not both if
     you're short on budget)
  3. `compose_itinerary` with everything you have

Rules:
- NEVER retry a tool that returned count:0 or error. Move on.
- For `search_flights`, pass IATA codes (e.g. "FCO", "JFK"), never city
  names. If you don't know the IATA code for the origin, SKIP flights —
  do not guess.
- When you call `compose_itinerary`, infer reasonable defaults from the
  goal: number of days, travelers, budget (eur/day), style (Balanced,
  Luxury, Adventure, Relaxed), interests list, food prefs list.
- Dates: if unspecified, assume a 7-day trip starting 30 days from today.
- Build `enriched_context` by concatenating the short tool outputs you've
  seen (hotels, restaurants, attractions).
- Keep the final user-facing message to ONE sentence.
"""


def run_agent(req: AgentPlanRequest, max_steps: int = 8) -> AgentPlanResponse:
    """Run the function-calling loop."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": req.goal},
    ]

    steps: list[AgentStep] = []
    final_plan: StructuredItinerary | None = None
    final_message = ""

    for step_i in range(max_steps):
        # On the very last iteration, force the model to call compose_itinerary
        # so we never exit the loop without a plan.
        is_last = step_i == max_steps - 1
        if is_last and final_plan is None:
            tool_choice: Any = {"type": "function", "function": {"name": "compose_itinerary"}}
            messages.append({
                "role": "system",
                "content": (
                    "This is your LAST step. You MUST call compose_itinerary now "
                    "with the best data you have. Infer any missing fields from the "
                    "user goal and tool outputs above."
                ),
            })
        else:
            tool_choice = "auto"

        resp = openai_client().chat.completions.create(
            model=config.CHAT_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice=tool_choice,
            temperature=0.3,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            final_message = msg.content or ""
            messages.append({"role": "assistant", "content": final_message})
            break

        # Record the assistant message with tool calls so the loop can continue.
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            impl = TOOL_IMPL.get(name)
            if impl is None:
                output: dict = {"error": f"unknown tool {name}"}
            else:
                try:
                    output = impl(**args)
                except Exception as e:  # surface to the model so it can recover
                    output = {"error": f"{type(e).__name__}: {e}"}

            if name == "compose_itinerary" and "days" in output:
                try:
                    final_plan = StructuredItinerary.model_validate(output)
                except Exception:
                    pass

            steps.append(AgentStep(
                tool=name,
                args=args,
                output_summary=json.dumps(output)[:400],
            ))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(output)[:6000],  # cap tool output size
            })

        # If the model has now produced a plan, end the loop early — no
        # point continuing to burn tokens.
        if final_plan is not None:
            final_message = final_message or "Itinerary composed successfully."
            break

    # Safety net: if we still have no plan (e.g. the forced last step returned
    # unparseable JSON), synthesise one directly so the UI always shows
    # something usable.
    if final_plan is None:
        final_plan = _force_compose_from_goal(req.goal)
        if final_plan is not None:
            final_message = final_message or "Plan generated via safety fallback."

    if not final_message:
        final_message = "Agent finished."

    return AgentPlanResponse(steps=steps, final_plan=final_plan, final_message=final_message)


def _force_compose_from_goal(goal: str) -> StructuredItinerary | None:
    """
    Last-resort fallback: derive minimal ItineraryGenerateRequest params from
    the raw goal via a quick structured LLM call, then compose directly.
    """
    import datetime as _dt
    extract_prompt = f"""Extract trip parameters from this goal. Respond with JSON only.
Goal: "{goal}"

Schema:
{{
  "destination": "city name (string)",
  "days": integer (default 5),
  "travelers": integer (default 2),
  "style": "Balanced|Luxury|Adventure|Relaxed" (default "Balanced"),
  "interests": ["Culture","Food","Nature","Nightlife","Shopping"] subset,
  "food_prefs": list of strings (default []),
  "daily_budget": number EUR (default 150)
}}"""
    try:
        from .openai_client import chat_json
        params = chat_json(
            [{"role": "user", "content": extract_prompt}],
            max_tokens=400,
            temperature=0.1,
        )
    except Exception:
        return None

    today = _dt.date.today()
    depart = today + _dt.timedelta(days=30)
    days = int(params.get("days") or 5)
    ret = depart + _dt.timedelta(days=days)

    try:
        req = ItineraryGenerateRequest(
            destination=str(params.get("destination") or "Paris"),
            depart_date=depart.isoformat(),
            return_date=ret.isoformat(),
            days=days,
            travelers=int(params.get("travelers") or 2),
            style=str(params.get("style") or "Balanced"),
            interests=list(params.get("interests") or ["Culture", "Food"]),
            food_prefs=list(params.get("food_prefs") or []),
            daily_budget=float(params.get("daily_budget") or 150),
            enriched_context="",
            weather_summary="",
        )
        return generate_structured(req)
    except Exception:
        return None
