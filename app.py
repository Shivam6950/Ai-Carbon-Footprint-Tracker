import os
import matplotlib.pyplot as plt
import streamlit as st

try:
    from groq import Groq
except ImportError:
    Groq = None

# Simplified emission factors for project demonstration, not an official audit.
INDIA_GRID_CO2_PER_KWH = 0.7
FUEL_FACTORS = {"Petrol": 2.31, "Diesel": 2.68, "CNG": 2.0}
DIET_MONTHLY = {"Vegan": 80, "Vegetarian": 120, "Occasional Meat": 220,
                "Regular Meat": 350, "Heavy Meat": 500}
COOKING_MONTHLY = {"LPG": 90, "PNG": 70, "Electric": 40, "Biomass": 160}
SHOPPING_FACTORS = {"grocery": 0.01, "clothing": 0.03, "electronics": 0.08, "household": 0.02}
INDIA_AVG_MONTHLY = 170
WORLD_AVG_MONTHLY = 400
TREE_OFFSET_KG_PER_YEAR = 21

st.set_page_config(page_title="Carbon Footprint Tracker", page_icon="🌱", layout="wide")


def calculate(data):
    electricity = data["electricity"] * INDIA_GRID_CO2_PER_KWH * (0.6 if data["solar"] else 1)
    km, mode, fuel, mileage = data["distance"], data["transport"], data["fuel"], data["mileage"]
    if mode == "Bus":
        transport = km * 0.08
    elif mode == "Train":
        transport = km * 0.04
    elif mode in ("Car", "Bike") and fuel == "Electric":
        transport = km * 0.05
    elif mode in ("Car", "Bike") and mileage > 0:
        transport = km / mileage * FUEL_FACTORS.get(fuel, 0)
    else:
        transport = 0
    food = DIET_MONTHLY[data["diet"]] * data["members"]
    cooking = COOKING_MONTHLY[data["cooking"]] * data["members"]
    flights = (data["domestic_flights"] * 150 + data["international_flights"] * 1100) / 12
    shopping = sum(data[k] * SHOPPING_FACTORS[k] for k in SHOPPING_FACTORS)
    waste = 50 * (0.7 if data["recycle"] else 1) * (0.8 if data["compost"] else 1)
    parts = {"Electricity": electricity, "Transport": transport, "Food": food,
             "Cooking": cooking, "Flights": flights, "Shopping": shopping, "Waste": waste}
    return sum(parts.values()), parts


def status(total, members):
    benchmark = INDIA_AVG_MONTHLY * members
    if total < benchmark * .8:
        return "Good"
    if total < benchmark * 1.2:
        return "Average"
    if total < benchmark * 2:
        return "High"
    return "Critical"


def fallback_advice(data, breakdown):
    tips = {
        "Electricity": "Reduce electricity use: switch off idle devices, use efficient lighting, and choose energy-efficient appliances.",
        "Transport": "Combine errands, avoid unnecessary trips, and consider carpooling, public transport, walking, or cycling where practical.",
        "Food": "Try more plant-based meals, choose seasonal foods when practical, and plan meals to reduce food waste.",
        "Cooking": "Use pan lids, match pan size to the burner, and avoid leaving burners running longer than needed.",
        "Flights": "When practical, replace short flights with rail or other lower-emission transport and combine trips.",
        "Shopping": "Buy only what you need, repair or reuse items, and consider durable or second-hand products.",
        "Waste": "Sort recyclable materials and compost suitable food scraps where local facilities allow."
    }
    chosen = [tips[k] for k, v in sorted(breakdown.items(), key=lambda x: x[1], reverse=True) if v > 0][:5]
    if not chosen:
        chosen = ["Keep conserving energy, avoiding unnecessary travel, and reducing food waste."]
    return "### Practical recommendations\n" + "\n".join(f"{i}. {tip}" for i, tip in enumerate(chosen, 1)) + \
        "\n\n*These built-in recommendations require no API key.*"


def get_ai_advice(data, breakdown, total):
    try:
        api_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", "")).strip()
    except Exception:
        api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key or Groq is None:
        return fallback_advice(data, breakdown), False

    prompt = f"""
Give 4-5 practical personalized sustainability recommendations. Prioritize the largest contributors.
Use simple language, treat values as estimates, and do not invent exact savings.
Household: {data}
Monthly emissions breakdown (kg CO2): {breakdown}
Estimated total: {total:.1f} kg CO2/month.
AC hours are collected for context but are not separately included in the formula.
"""
    try:
        client = Groq(api_key=api_key)
        result = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": "You are a practical, concise sustainability advisor. Be realistic."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.5,
        )
        answer = result.choices[0].message.content
        if answer and answer.strip():
            return answer.strip(), True
    except Exception:
        # If API key, model, network, or free quota fails, never break the calculator.
        pass
    return fallback_advice(data, breakdown) + \
        "\n\n*Hosted AI is unavailable or its free limit may have been reached; showing built-in advice instead.*", False


st.title("🌱 Carbon Footprint Tracker")
st.caption("Estimate your household's monthly footprint and get sustainability recommendations.")
st.info("These are simplified estimates using approximate factors, not an official carbon audit.")

with st.form("footprint_form"):
    st.subheader("Your household")
    c1, c2, c3 = st.columns(3)
    with c1:
        members = st.number_input("Household members", 1, 100, 2, step=1)
        diet = st.selectbox("Diet", list(DIET_MONTHLY), index=1)
        cooking = st.selectbox("Cooking fuel", list(COOKING_MONTHLY))
    with c2:
        transport = st.selectbox("Main transport", ["Car", "Bike", "Bus", "Train", "None"])
        fuel = st.selectbox("Vehicle fuel", ["Petrol", "Diesel", "CNG", "Electric", "N/A"])
        distance = st.number_input("Monthly travel distance (km)", min_value=0.0, value=300.0, step=25.0)
        mileage = st.number_input("Vehicle mileage (km/l)", min_value=0.0, value=15.0, step=1.0)
    with c3:
        electricity = st.number_input("Electricity usage (kWh/month)", min_value=0.0, value=150.0, step=10.0)
        ac_hours = st.number_input("AC usage (hours/day)", min_value=0.0, max_value=24.0, value=2.0, step=0.5)
        domestic_flights = st.number_input("Domestic flights per household/year", min_value=0.0, value=0.0, step=1.0)
        international_flights = st.number_input("International flights per household/year", min_value=0.0, value=0.0, step=1.0)

    st.subheader("Monthly spending (₹)")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        grocery = st.number_input("Groceries", min_value=0.0, value=5000.0, step=500.0)
    with s2:
        clothing = st.number_input("Clothing", min_value=0.0, value=1000.0, step=500.0)
    with s3:
        electronics = st.number_input("Electronics", min_value=0.0, value=500.0, step=100.0)
    with s4:
        household = st.number_input("Household goods", min_value=0.0, value=1000.0, step=100.0)

    st.subheader("Habits")
    h1, h2, h3 = st.columns(3)
    with h1:
        recycle = st.checkbox("I recycle")
    with h2:
        compost = st.checkbox("I compost food waste")
    with h3:
        solar = st.checkbox("I use rooftop solar")
    submitted = st.form_submit_button("Calculate my footprint", type="primary", use_container_width=True)

if submitted:
    if transport in ("Car", "Bike") and fuel not in ("Electric", "N/A") and distance > 0 and mileage <= 0:
        st.error("Enter vehicle mileage greater than zero for a petrol, diesel, or CNG vehicle.")
        st.stop()

    data = {
        "members": int(members), "diet": diet, "cooking": cooking, "transport": transport,
        "fuel": fuel, "distance": float(distance), "mileage": float(mileage),
        "electricity": float(electricity), "ac_hours": float(ac_hours),
        "domestic_flights": float(domestic_flights), "international_flights": float(international_flights),
        "grocery": float(grocery), "clothing": float(clothing), "electronics": float(electronics),
        "household": float(household), "recycle": recycle, "compost": compost, "solar": solar,
    }
    total, breakdown = calculate(data)
    trees = total * 12 / TREE_OFFSET_KG_PER_YEAR

    st.divider()
    st.subheader("Your results")
    k1, k2, k3 = st.columns(3)
    k1.metric("Monthly footprint", f"{total:,.1f} kg CO₂")
    k2.metric("Status", status(total, int(members)))
    k3.metric("Trees to offset yearly emissions*", f"{trees:,.0f}")

    left, right = st.columns(2)
    with left:
        st.markdown("**Monthly comparison**")
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = ["Your household", "India reference", "World reference"]
        values = [total, INDIA_AVG_MONTHLY * int(members), WORLD_AVG_MONTHLY * int(members)]
        bars = ax.bar(labels, values)
        ax.set_ylabel("kg CO₂ / month")
        ax.tick_params(axis="x", rotation=12)
        ax.bar_label(bars, fmt="%.0f")
        fig.tight_layout()
        st.pyplot(fig, clear_figure=True)
        plt.close(fig)

    with right:
        st.markdown("**Emissions breakdown**")
        fig, ax = plt.subplots(figsize=(6, 4))
        positive = [(k, v) for k, v in breakdown.items() if v > 0]
        if positive:
            ax.pie([v for _, v in positive], labels=[k for k, _ in positive], autopct="%1.1f%%")
        else:
            ax.text(.5, .5, "No emissions to chart", ha="center", va="center")
        fig.tight_layout()
        st.pyplot(fig, clear_figure=True)
        plt.close(fig)

    st.markdown("**Category details (kg CO₂/month)**")
    st.dataframe(
        [{"Category": k, "Estimated emissions": round(v, 2)} for k, v in breakdown.items()],
        use_container_width=True, hide_index=True
    )

    st.subheader("🤖 AI Sustainability Advisor")
    with st.spinner("Preparing recommendations…"):
        advice, used_ai = get_ai_advice(data, breakdown, total)
    st.caption("Recommendations generated by hosted AI." if used_ai else "Using built-in recommendations; no API credits required.")
    st.markdown(advice)
    st.caption("*Tree offset is illustrative, based on 21 kg CO₂ per tree per year. Actual sequestration varies. AC hours are not separately included in the current formula.*")

with st.expander("About the calculation"):
    st.markdown(
        "- Electricity, transport, diet, cooking, flights, shopping, and waste use simplified factors.\n"
        "- AC hours are collected for context but do not independently affect the calculation.\n"
        "- Tree-offset estimates and India/world averages are illustrative project assumptions.\n"
        "- Built-in recommendations remain available if hosted AI is not configured or reaches its usage limit."
    )
