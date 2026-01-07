import pandas as pd
from typing import List, Optional

def load_fresh_fr(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

def load_master_map_item(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    # Normalize column names for easier access
    df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
    return df

def load_sr_data(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

def map_item_to_material_codes(item_id: int, master_map: pd.DataFrame) -> List[str]:
    row = master_map[master_map['item_id'] == item_id]
    if row.empty:
        return []
    codes = []
    if 'material_code' in row:
        codes += row['material_code'].astype(str).tolist()
    if 'material_code2' in row:
        codes += row['material_code2'].astype(str).tolist()
    return [code for code in codes if pd.notna(code) and code != 'nan']

def find_sr_entry(po_number: str, material_codes: List[str], sr_data: pd.DataFrame) -> Optional[pd.Series]:
    for code in material_codes:
        match = sr_data[(sr_data['po_number'] == po_number) & (sr_data['Material Code'].astype(str) == code)]
        if not match.empty:
            return match.iloc[0]
    return None
