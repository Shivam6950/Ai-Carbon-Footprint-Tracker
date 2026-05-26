import ollama
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt

# -----------------------------
# Emission factors (approximate)
# -----------------------------
INDIA_GRID_CO2_PER_KWH = 0.7
PETROL_CO2_PER_L = 2.31
DIESEL_CO2_PER_L = 2.68
CNG_CO2_PER_L_EQ = 2.0
BUS_CO2_PER_KM = 0.08
TRAIN_CO2_PER_KM = 0.04
DOMESTIC_FLIGHT_CO2 = 150
INTERNATIONAL_FLIGHT_CO2 = 1100
TREE_OFFSET_KG_PER_YEAR = 21
WORLD_AVG_MONTHLY = 400
INDIA_AVG_MONTHLY = 170

DIET_MONTHLY = {
    'Vegan': 80,
    'Vegetarian': 120,
    'Occasional Meat': 220,
    'Regular Meat': 350,
    'Heavy Meat': 500,
}

COOKING_MONTHLY = {
    'LPG': 90,
    'PNG': 70,
    'Electric': 40,
    'Biomass': 160,
}

SHOPPING_FACTORS = {
    'grocery': 0.01,
    'clothing': 0.03,
    'electronics': 0.08,
    'household': 0.02,
}


def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0


def transport_emissions(mode, fuel, km, mileage):
    if mode == 'None':
        return 0
    if mode == 'Bus':
        return km * BUS_CO2_PER_KM
    if mode == 'Train':
        return km * TRAIN_CO2_PER_KM
    if mileage <= 0:
        return 0
    litres = km / mileage
    if fuel == 'Petrol':
        return litres * PETROL_CO2_PER_L
    if fuel == 'Diesel':
        return litres * DIESEL_CO2_PER_L
    if fuel == 'CNG':
        return litres * CNG_CO2_PER_L_EQ
    if fuel == 'Electric':
        return km * 0.05
    return 0


def ai_suggestions_with_ollama(data, breakdown, total):
    prompt = f"""
You are an expert carbon footprint and sustainability consultant.

Analyze this user's carbon footprint data and provide highly personalized recommendations.

User profile:
Household members: {data['members']}
Diet: {data['diet']}
Transport: {data['transport']}
Fuel: {data['fuel']}
Monthly travel distance: {data['distance']} km
Vehicle mileage: {data['mileage']} km/l
Electricity usage: {data['electricity']} kWh/month
AC usage: {data['ac_hours']} hours/day
Cooking fuel: {data['cooking']}
Domestic flights/year: {data['domestic_flights']}
International flights/year: {data['international_flights']}
Groceries spending: ₹{data['grocery']}
Clothing spending: ₹{data['clothing']}
Electronics spending: ₹{data['electronics']}
Household goods spending: ₹{data['household']}
Recycling: {data['recycle']}
Composting: {data['compost']}
Solar usage: {data['solar']}

Calculated emissions breakdown:
{breakdown}

Total monthly footprint:
{total:.2f} kg CO₂

Instructions:
- Identify biggest emission contributors
- Give personalized practical recommendations
- Avoid generic advice
- Mention estimated impact where possible
- Keep response between 150–250 words
"""
    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}]
        )
        return response['message']['content']
    except Exception as e:
        return f"AI advisor unavailable: {str(e)}"


def calculate(data):
    electricity = data['electricity'] * INDIA_GRID_CO2_PER_KWH
    if data['solar']:
        electricity *= 0.6

    transport = transport_emissions(data['transport'], data['fuel'], data['distance'], data['mileage'])
    food = DIET_MONTHLY[data['diet']] * data['members']
    cooking = COOKING_MONTHLY[data['cooking']] * data['members']
    flights = ((data['domestic_flights'] * DOMESTIC_FLIGHT_CO2) +
               (data['international_flights'] * INTERNATIONAL_FLIGHT_CO2)) / 12

    shopping = (
        data['grocery'] * SHOPPING_FACTORS['grocery'] +
        data['clothing'] * SHOPPING_FACTORS['clothing'] +
        data['electronics'] * SHOPPING_FACTORS['electronics'] +
        data['household'] * SHOPPING_FACTORS['household']
    )

    waste = 50
    if data['recycle']:
        waste *= 0.7
    if data['compost']:
        waste *= 0.8

    total = electricity + transport + food + cooking + flights + shopping + waste

    breakdown = {
        'electricity': electricity,
        'transport': transport,
        'food': food,
        'cooking': cooking,
        'flights': flights,
        'shopping': shopping,
        'waste': waste,
    }
    return total, breakdown


def status(total, members):
    benchmark = INDIA_AVG_MONTHLY * members
    if total < benchmark * 0.8:
        return 'Good'
    elif total < benchmark * 1.2:
        return 'Average'
    elif total < benchmark * 2:
        return 'High'
    return 'Critical'


def show_graphs(total, members, breakdown):
    plt.figure(figsize=(6, 4))
    plt.bar(['You', 'India Avg', 'World Avg'], [total, INDIA_AVG_MONTHLY * members, WORLD_AVG_MONTHLY * members])
    plt.ylabel('kg CO₂ / month')
    plt.title('Comparison')
    plt.tight_layout()
    plt.show(block=False)

    plt.figure(figsize=(6, 5))
    plt.pie(list(breakdown.values()), labels=list(breakdown.keys()), autopct='%1.1f%%')
    plt.title('Emission Breakdown')
    plt.tight_layout()
    plt.show(block=False)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('Carbon Footprint Tracker v2')
        self.root.geometry('820x900')

        self.entries = {}
        self.current_request_id = None
        self.build_ui()

    def add_entry(self, parent, label, row):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=4)
        e = tk.Entry(parent)
        e.grid(row=row, column=1, pady=4)
        return e

    def build_ui(self):
        f = tk.Frame(self.root)
        f.pack(pady=10)

        self.entries['members'] = self.add_entry(f, 'Household Members', 0)

        tk.Label(f, text='Diet').grid(row=1, column=0, sticky='w')
        self.diet = ttk.Combobox(f, values=list(DIET_MONTHLY.keys()), state='readonly')
        self.diet.grid(row=1, column=1)
        self.diet.current(1)

        tk.Label(f, text='Transport').grid(row=2, column=0, sticky='w')
        self.transport = ttk.Combobox(f, values=['Car', 'Bike', 'Bus', 'Train', 'None'], state='readonly')
        self.transport.grid(row=2, column=1)
        self.transport.current(0)

        tk.Label(f, text='Fuel').grid(row=3, column=0, sticky='w')
        self.fuel = ttk.Combobox(f, values=['Petrol', 'Diesel', 'CNG', 'Electric', 'N/A'], state='readonly')
        self.fuel.grid(row=3, column=1)
        self.fuel.current(0)

        self.entries['distance'] = self.add_entry(f, 'Monthly Distance (km)', 4)
        self.entries['mileage'] = self.add_entry(f, 'Mileage (km/l)', 5)
        self.entries['electricity'] = self.add_entry(f, 'Electricity (kWh/month)', 6)
        self.entries['ac_hours'] = self.add_entry(f, 'AC Hours/day', 7)

        tk.Label(f, text='Cooking Fuel').grid(row=8, column=0, sticky='w')
        self.cooking = ttk.Combobox(f, values=list(COOKING_MONTHLY.keys()), state='readonly')
        self.cooking.grid(row=8, column=1)
        self.cooking.current(0)

        self.entries['domestic_flights'] = self.add_entry(f, 'Domestic Flights/year', 9)
        self.entries['international_flights'] = self.add_entry(f, 'International Flights/year', 10)
        self.entries['grocery'] = self.add_entry(f, 'Groceries ₹/month', 11)
        self.entries['clothing'] = self.add_entry(f, 'Clothing ₹/month', 12)
        self.entries['electronics'] = self.add_entry(f, 'Electronics ₹/month', 13)
        self.entries['household'] = self.add_entry(f, 'Household Goods ₹/month', 14)

        self.recycle = tk.BooleanVar()
        self.compost = tk.BooleanVar()
        self.solar = tk.BooleanVar()

        tk.Checkbutton(f, text='Recycling', variable=self.recycle).grid(row=15, column=0, sticky='w')
        tk.Checkbutton(f, text='Composting', variable=self.compost).grid(row=15, column=1, sticky='w')
        tk.Checkbutton(f, text='Rooftop Solar', variable=self.solar).grid(row=16, column=0, sticky='w')

        tk.Button(self.root, text='Calculate Footprint', command=self.run_calc, bg='green', fg='white').pack(pady=12)

        self.output = tk.Text(self.root, height=18, width=95)
        self.output.pack(pady=10)

    def generate_ai_advice(self, data, breakdown, total):
        request_id = id(data)
        advice = ai_suggestions_with_ollama(data, breakdown, total)

        if request_id != self.current_request_id:
            return

        self.output.after(
            0,
            lambda: self.output.insert(
                tk.END,
                "AI Sustainability Advisor:" + advice + "")
        )

    def run_calc(self):
        try:
            data = {
                'members': int(safe_float(self.entries['members'].get())),
                'diet': self.diet.get(),
                'transport': self.transport.get(),
                'fuel': self.fuel.get(),
                'distance': safe_float(self.entries['distance'].get()),
                'mileage': safe_float(self.entries['mileage'].get()),
                'electricity': safe_float(self.entries['electricity'].get()),
                'ac_hours': safe_float(self.entries['ac_hours'].get()),
                'cooking': self.cooking.get(),
                'domestic_flights': safe_float(self.entries['domestic_flights'].get()),
                'international_flights': safe_float(self.entries['international_flights'].get()),
                'grocery': safe_float(self.entries['grocery'].get()),
                'clothing': safe_float(self.entries['clothing'].get()),
                'electronics': safe_float(self.entries['electronics'].get()),
                'household': safe_float(self.entries['household'].get()),
                'recycle': self.recycle.get(),
                'compost': self.compost.get(),
                'solar': self.solar.get(),
            }

            if data['members'] <= 0:
                raise ValueError('Household members must be greater than 0')
            if data['electricity'] <= 0:
                raise ValueError('Enter valid electricity usage in kWh')
            if data['transport'] in ['Car', 'Bike'] and data['distance'] <= 0:
                raise ValueError('Enter monthly travel distance')
            if data['transport'] in ['Car', 'Bike'] and data['mileage'] <= 0:
                raise ValueError('Enter valid vehicle mileage')

            total, breakdown = calculate(data)
            level = status(total, data['members'])
            trees = total * 12 / TREE_OFFSET_KG_PER_YEAR

            self.output.delete('1.0', tk.END)
            self.current_request_id = id(data)

            self.output.insert(tk.END, f'Total Carbon Footprint: {total:.2f} kg CO₂/month')
            self.output.insert(tk.END, f'Status: {level}')
            self.output.insert(tk.END, f'India Average ({data["members"]} members): {INDIA_AVG_MONTHLY * data["members"]:.2f} kg/month')
            self.output.insert(tk.END, f'World Average ({data["members"]} members): {WORLD_AVG_MONTHLY * data["members"]:.2f} kg/month')
            self.output.insert(tk.END, f'Trees needed to offset yearly emissions: {trees:.0f}')
            self.output.insert(tk.END, 'Breakdown:')

            for k, v in breakdown.items():
                self.output.insert(tk.END, f' - {k.title()}: {v:.2f} kg')

            self.output.insert(
                tk.END,
                "" + "-" * 50 + "AI Sustainability Advisor is thinking...")

            show_graphs(total, data['members'], breakdown)

            threading.Thread(
                target=self.generate_ai_advice,
                args=(data, breakdown, total),
                daemon=True
            ).start()
        except Exception as e:
            messagebox.showerror('Error', f'Check your inputs.\n{e}')


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()

