import pandas as pd
from typing import List

def load_fresh_soh(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
    return df

def map_city_name(city: str) -> str:
    # Hardcoded city mapping, add more as needed
    city_map = {
        'surat': 'ahmedabad',
        "ahmedabad": "ahmedabad", 
        "surat": "ahmedabad", 
        "bengaluru": "bangalore", 
        "chennai": "chennai", 
        "coimbatore": "coimbatore", 
        "bhubaneswar": "cuttack", 
        "dasna": "delhi", 
        "farukhnagar": "delhi", 
        "kundli": "delhi", 
        "noida": "ghaziabad", 
        "bhopal": "ghaziabad", 
        "jaipur": "ghaziabad", 
        "guwahati": "guwahati", 
        "hyderabad": "hyderabad", 
        "kolkata": "kolkata", 
        "lucknow": "lucknow", 
        "ludhiana": "lucknow", 
        "varanasi": "lucknow", 
        "mumbai": "mumbai", 
        "pune": "pune", 
        "goa": "pune", 
        "indore": "pune", 
        "nagpur": "pune", 
        "patna": "ranchi", 
        "ranchi": "ranchi", 
        "visakhapatnam": "vijayawada", 
        "dehradun": "zirakpur", 
        "rajpura": "zirakpur"
        # Add more mappings here
    }
    if pd.isna(city):
        return city
    city_str = str(city).strip()
    return city_map.get(city_str.lower(), city_str)

