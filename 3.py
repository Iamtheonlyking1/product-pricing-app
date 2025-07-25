
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Product Price Calculator", layout="wide")

# --- SESSION STATE TO TRACK MULTIPLE PRODUCTS ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- LOAD EXCEL FILE ---
@st.cache_resource
def load_excel(file_path):
    excel = pd.ExcelFile(file_path)
    sheets = excel.sheet_names
    return sheets, excel

@st.cache_data
def clean_sheet(file_path, sheet_name):
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    for col in df.columns:
        if isinstance(col, str) and col.strip().lower() in ['product name', 'variation']:
            df[col] = df[col].fillna(method='ffill')
    if sheet_name.lower() == "portable gantry crane" and "Unnamed: 6" in df.columns:
        df = df.rename(columns={"Unnamed: 6": "Nylon Wheel Price"})
    return df

# --- MAIN ---
file_path = "Price and products last2.xlsx"
sheet_names, excel_file = load_excel(file_path)

st.title("📦 Product Price Calculator")

# --- SHEET SELECTION ---
selected_sheet = st.selectbox("Select Product Type", sheet_names)
df = clean_sheet(file_path, selected_sheet)

# --- RANGE SELECTION ---
range_col = next((col for col in df.columns if "range" in str(col).lower()), None)
if range_col:
    available_ranges = df[range_col].dropna().unique()
    selected_range = st.selectbox("Available Ranges", available_ranges)
    matched_rows = df[df[range_col] == selected_range].reset_index(drop=True)
else:
    matched_rows = df
	# Show all available products for the selected range
st.markdown("### 📋 Products Matching Selected Range")
display_cols = [col for col in matched_rows.columns if not str(col).lower().startswith("unnamed")]
st.dataframe(matched_rows[display_cols], use_container_width=True)



# --- PRODUCT ROW SELECTION ---
display_cols = [col for col in matched_rows.columns if "model" in col.lower() or "clear span" in col.lower()]
display_texts = []
for idx, row in matched_rows.iterrows():
    label_parts = [f"{col}: {row[col]}" for col in display_cols if pd.notna(row[col])]
    display_texts.append(f"{idx + 1}. " + " | ".join(label_parts) if label_parts else f"{idx + 1}")
selected_index = st.selectbox("Select Product Option", range(len(display_texts)), format_func=lambda i: display_texts[i])
selected_product = matched_rows.iloc[selected_index]
st.dataframe(pd.DataFrame(selected_product).transpose())

# --- PRICING LOGIC ---
sheet = selected_sheet.lower()
base_price = 0
extra_cost = 0
addons_total = 0
discount = 0.0

# === Product-specific logic ===
if "chain pulley block" in sheet or "monorail travelling trolley" in sheet:
    lift = st.number_input("Enter required lift (in meters)", min_value=1.0, value=3.0, step=0.5)
    base_col = next((col for col in selected_product.index if "price" in col.lower()), None)
    base_price = float(selected_product[base_col]) if base_col else 0
    if lift > 3:
        extra_col = next((col for col in selected_product.index if "extra" in col.lower()), None)
        if extra_col and pd.notna(selected_product[extra_col]):
            extra_cost = round((lift - 3) * float(selected_product[extra_col]), 2)

elif "electric chain hoist" in sheet:
    hoist_type = st.radio("Select Hoist Type", ["Fixed Type", "Cross Travel Manual", "All Operation Electrical"])
    if hoist_type == "Fixed Type":
        base_col, extra_col = "Price (in Rs.)", "Unnamed: 6"
    elif hoist_type == "Cross Travel Manual":
        base_col, extra_col = "Unnamed: 7", "Unnamed: 8"
    else:
        base_col, extra_col = "Unnamed: 9", "Unnamed: 10"
    base_price = float(selected_product.get(base_col, 0))
    lift = st.number_input("Enter required lift (in meters)", min_value=1.0, value=3.0, step=0.5)
    if lift > 3 and pd.notna(selected_product.get(extra_col)):
        extra_cost = round((lift - 3) * float(selected_product[extra_col]), 2)

elif "electric wire rope hoist" in sheet:
    hoist_type = st.radio("Select Hoist Type", ["Fixed Type", "All Operation Electrical"])
    default_lift = selected_product.get("Lift in Mtr.", 12)
    lift = st.number_input("Enter required lift (in meters)", min_value=1.0, value=float(default_lift), step=0.5)
    base_col = "Price (in Rs.)" if hoist_type == "Fixed Type" else "Unnamed: 7"
    extra_col = "Unnamed: 6" if hoist_type == "Fixed Type" else "Unnamed: 8"

    def get_price_for_lift(lvl, col):
        row = df[(df["Model"] == selected_product["Model"]) & (df["Lift in Mtr."] == lvl)]
        if not row.empty and pd.notna(row.iloc[0].get(col)):
            return float(row.iloc[0][col])
        return None

    if lift <= 6:
        base_price = get_price_for_lift(6.0, base_col)
    elif lift <= 9:
        base_price = get_price_for_lift(9.0, base_col)
    elif lift <= 12:
        base_price = get_price_for_lift(12.0, base_col)
    else:
        base_price = get_price_for_lift(12.0, base_col)
        if pd.notna(selected_product.get(extra_col)):
            extra_cost = round((lift - 12) * float(selected_product[extra_col]), 2)

    # Add-ons
    addons = {
        "V3F (MH)": "Unnamed: 9",
        "V3F (AOE)": "Unnamed: 10",
        "CT Brake": "Unnamed: 11"
    }
    if hoist_type == "Fixed Type":
        addons["2Way to 6Way Panel Upgrade"] = "Unnamed: 12"
    else:
        addons["4Way to 6Way Panel Upgrade"] = "Unnamed: 13"
    for label, col in addons.items():
        if col in selected_product and pd.notna(selected_product[col]):
            if st.checkbox(f"Add {label} (₹{selected_product[col]:,.0f})"):
                addons_total += float(selected_product[col])

elif "electric winch machine" in sheet:
    base_price = float(selected_product.get("Price (in Rs.)", 0))
    for label, key in [("VFD", "vfd"), ("SLI", "sli")]:
        col = next((c for c in selected_product.index if key in c.lower()), None)
        if col and pd.notna(selected_product[col]):
            if st.checkbox(f"Add {label} (₹{selected_product[col]:,.0f})"):
                addons_total += float(selected_product[col])

elif "portable gantry crane" in sheet:
    wheel_type = st.radio("Wheel Type", ["Cast", "Nylon"])
    if wheel_type == "Nylon" and pd.notna(selected_product.get("Nylon Wheel Price")):
        base_price = float(selected_product["Nylon Wheel Price"])
    else:
        base_price = float(selected_product.get("Price (in Rs.)", 0))

else:
    base_col = next((col for col in selected_product.index if "price" in col.lower()), None)
    base_price = float(selected_product[base_col]) if base_col else 0

# --- DISCOUNT AND SUMMARY ---
discount = st.number_input("Enter discount (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.5)
total_price = base_price + extra_cost + addons_total
discounted = round(total_price * (1 - discount / 100), 2)
gst = round(discounted * 0.18, 2)
final = round(discounted + gst, 2)

st.markdown("### 💰 Final Price Breakdown")
st.write(f"**Base + Extras:** ₹{total_price:,.2f}")
st.write(f"**Discount ({discount}%):** -₹{total_price - discounted:,.2f}")
st.write(f"**Price After Discount:** ₹{discounted:,.2f}")
st.write(f"**+18% GST:** ₹{gst:,.2f}")
st.success(f"**Total Payable:** ₹{final:,.2f}")

# --- ADD TO QUOTE ---
if st.button("Add to Quote"):
    st.session_state.cart.append({
        "Product": selected_sheet,
        "Model": selected_product.get("Model", "N/A"),
	"Base + Extras (₹)": total_price,
    	"Discounted (₹)": discounted,
        "Final Price (₹)": final
    })
    st.success("Added to quote! You can now add another product.")

# --- SHOW SUMMARY ---
if len(st.session_state.cart) > 0:
    st.markdown("---")
    if st.button("Show Combined Quote Summary"):
        quote_df = pd.DataFrame(st.session_state.cart)
        st.markdown("### 🧾 Combined Quote")
        st.dataframe(quote_df)

        total_discounted = quote_df["Discounted (₹)"].sum()
        total_final = quote_df["Final Price (₹)"].sum()

        st.success(f"**Total (After Discount, Before GST): ₹{total_discounted:,.2f}**")
        st.success(f"**Total Payable (incl. GST): ₹{total_final:,.2f}**")

    if st.button("Clear All Quotes"):
        st.session_state.cart = []
        st.rerun()
