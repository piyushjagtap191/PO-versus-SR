import streamlit as st
import pandas as pd
from data_processing import load_fresh_fr, load_master_map_item, load_sr_data, map_item_to_material_codes, find_sr_entry
from soh_processing import load_fresh_soh, map_city_name

def main():
    st.title("PO vs SR Data Dashboard")
    st.markdown("Upload all four Excel files to begin analysis.")
    uploaded_fresh_fr = st.file_uploader("Upload Fresh_FR.xlsx", type=["xlsx"])
    uploaded_fresh_soh = st.file_uploader("Upload Fresh_SOH.xlsx", type=["xlsx"])
    uploaded_master_map = st.file_uploader("Upload Master_Map_Item.xlsx", type=["xlsx"])
    uploaded_sr_data = st.file_uploader("Upload SR_Data.xlsx", type=["xlsx"])

    if not (uploaded_fresh_fr and uploaded_fresh_soh and uploaded_master_map and uploaded_sr_data):
        st.info("Please upload all four files to proceed.")
        return

    fresh_fr = pd.read_excel(uploaded_fresh_fr)
    fresh_soh = pd.read_excel(uploaded_fresh_soh)
    master_map = pd.read_excel(uploaded_master_map)
    sr_data = pd.read_excel(uploaded_sr_data)

    # Normalize columns for robust matching
    fresh_fr.columns = [str(col).strip().lower().replace(' ', '_') for col in fresh_fr.columns]
    sr_data.columns = [str(col).strip().lower().replace(' ', '_') for col in sr_data.columns]
    master_map.columns = [str(col).strip().lower().replace(' ', '_') for col in master_map.columns]
    fresh_soh.columns = [str(col).strip().lower().replace(' ', '_') for col in fresh_soh.columns]

    results = []
    def normalize_id(val):
        # Convert to string, strip, and remove decimals if present
        try:
            return str(int(float(val))).strip()
        except:
            return str(val).strip()

    def normalize_code(val):
        # Convert to string, strip, and remove decimals if present
        try:
            return str(int(float(val))).strip()
        except:
            return str(val).strip()

    # Prepare a mapping from item_id to product name (column 'b')
    master_map['item_id_norm'] = master_map['item_id'].apply(normalize_id)
    itemid_to_product = dict(zip(master_map['item_id_norm'], master_map['b']))

    for _, row in fresh_fr.iterrows():
        po_number = normalize_id(row['po_number'])
        item_id = normalize_id(row['item_id'])
        po_qty = row['po_qty']
        # Get product name from mapping
        product_name = itemid_to_product.get(item_id, '')
        # Get all material codes for this item_id
        map_row = master_map[master_map['item_id_norm'] == item_id]
        material_codes = []
        if not map_row.empty:
            material_codes += map_row['material_code'].apply(normalize_code).tolist()
            if 'material_code2' in map_row:
                material_codes += map_row['material_code2'].apply(normalize_code).tolist()
        material_codes = [code for code in material_codes if code and code.lower() != 'nan']
        # Filter SR data for this PO number (as string)
        sr_data['po_number_norm'] = sr_data['po_number'].apply(normalize_id)
        sr_data['material_code_norm'] = sr_data['material_code'].apply(normalize_code)
        sr_po_matches = sr_data[sr_data['po_number_norm'] == po_number]
        # Find all SR rows with a matching material code (normalized)
        sr_code_matches = sr_po_matches[sr_po_matches['material_code_norm'].isin(material_codes)]
        if not sr_code_matches.empty:
            supplied_qty = sr_code_matches['quantity'].sum()
            if po_qty == supplied_qty:
                status = "Fully Serviced"
            elif po_qty > supplied_qty:
                status = "Partially Serviced"
            else:
                status = "Over Supplied"
            sr_info = sr_code_matches.iloc[0].to_dict()
            result = {**row.to_dict(), 'name_of_the_product': product_name, **sr_info, 'Supplied_Qty': supplied_qty, 'Status': status}
        else:
            result = {**row.to_dict(), 'name_of_the_product': product_name, 'Supplied_Qty': 0, 'Status': 'Not Found'}
        results.append(result)

    result_df = pd.DataFrame(results)
    # Move 'name_of_the_product' after 'item_id'
    cols = result_df.columns.tolist()
    if 'name_of_the_product' in cols:
        cols.remove('name_of_the_product')
        idx = cols.index('item_id') + 1 if 'item_id' in cols else 1
        cols.insert(idx, 'name_of_the_product')
        result_df = result_df[cols]
    st.dataframe(result_df)

    # --- New Table: Partially Serviced and Not Found with Expiry > Today ---
    today = pd.Timestamp.today().normalize()
    # Map city names in result_df
    result_df['city_mapped'] = result_df['city'].apply(map_city_name)
    # Filter for partially serviced and all not found with expiry > today
    filtered = result_df[((result_df['Status'] == 'Partially Serviced') |
                         ((result_df['Status'] == 'Not Found') & (pd.to_datetime(result_df['po_expiry_date']) > today)))]
    # Add all Not Found entries with expiry > today, even if not partially serviced
    not_found = result_df[(result_df['Status'] == 'Not Found') & (pd.to_datetime(result_df['po_expiry_date']) > today)]
    filtered = pd.concat([filtered, not_found]).drop_duplicates()

    # Prepare new table rows
    new_rows = []
    for _, row in filtered.iterrows():
        item_id = str(row['item_id'])
        city = row['city_mapped']
        po_qty = row['po_qty']
        # Get product name from mapping
        product_name = itemid_to_product.get(normalize_id(item_id), '')
        # Map item_id to material codes
        map_row = master_map[master_map['item_id'].apply(lambda x: str(int(float(x))) if pd.notna(x) else '').astype(str) == str(int(float(item_id)))]
        material_codes = []
        if not map_row.empty:
            material_codes += map_row['material_code'].apply(lambda x: str(int(float(x))) if pd.notna(x) else '').tolist()
            if 'material_code2' in map_row:
                material_codes += map_row['material_code2'].apply(lambda x: str(int(float(x))) if pd.notna(x) else '').tolist()
        material_codes = [code for code in material_codes if code and code.lower() != 'nan']
        # Check Fresh_SOH for each material code (using 'total_qty')
        soh_found = False
        soh_qty = 0
        for code in material_codes:
            soh_match = fresh_soh[(fresh_soh['city'].str.lower() == city.lower()) &
                                  (fresh_soh['material_code'].apply(lambda x: str(int(float(x))) if pd.notna(x) else '').astype(str) == code)]
            if not soh_match.empty:
                soh_found = True
                soh_qty = soh_match['total_qty'].sum() if 'total_qty' in soh_match else soh_match.iloc[0].get('total_qty', 0)
                break
        if soh_found and soh_qty >= po_qty:
            supply_status = f"Can be supplied by nisin (Stock: {soh_qty}, PO Qty: {po_qty})"
        elif soh_found:
            supply_status = f"Not enough (Stock: {soh_qty}, PO Qty: {po_qty})"
        else:
            supply_status = "No stock info found"
        new_row = row.to_dict()
        new_row['name_of_the_product'] = product_name
        new_row['material_codes'] = ','.join(material_codes)
        new_row['soh_stock'] = soh_qty
        new_row['supply_status'] = supply_status
        # For Not Found entries, ensure SR columns like bill-to-street are blank
        if new_row.get('Status') == 'Not Found':
            for col in ['bill-to_street', 'name_of_the_employee', 'item', 'material_code', 'quantity']:
                if col in new_row:
                    new_row[col] = ''
        new_rows.append(new_row)
    # Move 'name_of_the_product' after 'item_id' in new table
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        cols2 = new_df.columns.tolist()
        if 'name_of_the_product' in cols2:
            cols2.remove('name_of_the_product')
            idx2 = cols2.index('item_id') + 1 if 'item_id' in cols2 else 1
            cols2.insert(idx2, 'name_of_the_product')
            new_df = new_df[cols2]
        # Only display the table once
        if 'partially_serviced_and_not_found_displayed' not in st.session_state:
            st.session_state['partially_serviced_and_not_found_displayed'] = True
            st.markdown('---')
            st.subheader('Partially Serviced & Not Found (with stock check)')
            st.dataframe(new_df)

    if new_rows:
        st.markdown('---')
        st.subheader('Partially Serviced & Not Found (with stock check)')
        st.dataframe(pd.DataFrame(new_rows))

if __name__ == "__main__":
    main()
