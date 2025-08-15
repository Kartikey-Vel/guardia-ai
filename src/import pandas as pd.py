import pandas as pd

# Define the budget categories and items with low/mid/high cost ranges (in INR)
budget_data = [
    # Land / Rent
    ["Land / Spot Rent (1st month + deposit)", "Monthly rent + deposit for location", 10000, 30000, 60000],
    
    # Vehicle
    ["Vehicle purchase + conversion", "Used tempo to new custom food truck", 150000, 450000, 1500000],
    
    # Equipment
    ["Kitchen equipment & smallwares", "Burners, fryer, fridge, tables, utensils", 100000, 250000, 600000],
    
    # Utilities setup
    ["Power, water, plumbing, gas setup", "LPG, wiring, tanks, inverter", 18000, 50000, 150000],
    
    # Initial inventory
    ["Initial raw materials & packaging", "Ingredients and packaging for 2-3 weeks", 20000, 40000, 60000],
    
    # Licenses & permits
    ["Licenses, permits, insurance", "FSSAI, trade license, fire NOC, insurance", 10000, 25000, 40000],
    
    # POS & marketing
    ["POS / billing system + branding", "POS tablet, signage, initial ads", 10000, 25000, 40000],
    
    # Staff wages (first month)
    ["Staff salaries (1-2 persons)", "First month salary buffer", 16000, 35000, 50000],
    
    # Contingency / buffer
    ["Contingency & working capital buffer", "1-2 months operating cost reserve", 50000, 100000, 200000],
]

# Create dataframe
df_budget = pd.DataFrame(budget_data, columns=["Category", "Description", "Low (INR)", "Mid (INR)", "High (INR)"])

# Calculate total for each range
df_budget.loc["Total"] = [
    "TOTAL", 
    "",
    df_budget["Low (INR)"].sum(),
    df_budget["Mid (INR)"].sum(),
    df_budget["High (INR)"].sum()
]

import caas_jupyter_tools
caas_jupyter_tools.display_dataframe_to_user(name="Food Truck Startup Budget (Kanpur)", dataframe=df_budget)
