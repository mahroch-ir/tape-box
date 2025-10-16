import streamlit as st
import pandas as pd
import os
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# ------------------ تنظیمات صفحه ------------------
st.set_page_config(page_title="مدیریت ابزارها", page_icon="🧰")
st.title("📦 مدیریت ابزارها")

# ------------------ مسیر فایل‌ها ------------------
DATA_FILE = "tools_data.csv"
IMAGES_DIR = "tool_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# ------------------ اتصال به Google Sheets ------------------
SERVICE_ACCOUNT_FILE = "service_account.json"

if os.path.exists(SERVICE_ACCOUNT_FILE):
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
else:
    st.error(f"⚠️ فایل {SERVICE_ACCOUNT_FILE} پیدا نشد.")
    st.stop()

gc = gspread.authorize(creds)

# اسم Google Sheet
SHEET_NAME = "tools_data"
try:
    sh = gc.open(SHEET_NAME)
except gspread.SpreadsheetNotFound:
    sh = gc.create(SHEET_NAME)
    sh.share(None, perm_type='anyone', role='writer')  # اختیاری: دسترسی برای همه

worksheet = sh.sheet1

# ------------------ بارگذاری داده‌ها ------------------
records = worksheet.get_all_records()
if records:
    df = pd.DataFrame(records)
else:
    df = pd.DataFrame(columns=["نام ابزار", "کد ابزار", "شماره قفسه", "مسیر عکس"])

# ------------------ منوی اصلی ------------------
menu = st.sidebar.selectbox("انتخاب صفحه", ["➕ افزودن ابزار", "📋 مشاهده ابزارها"])

# ------------------ افزودن ابزار ------------------
if menu == "➕ افزودن ابزار":
    st.header("افزودن ابزار جدید")
    name = st.selectbox("نام ابزار:", ["تپه", "بنوک"])
    code = st.text_input("کد ابزار:")
    shelf = st.number_input("شماره قفسه:", min_value=1, step=1)
    image_file = st.file_uploader("📸 انتخاب عکس ابزار", type=["jpg", "png", "jpeg"])

    if st.button("ذخیره ابزار"):
        if name and code and image_file:
            img_path = os.path.join(IMAGES_DIR, image_file.name)
            with open(img_path, "wb") as f:
                f.write(image_file.getbuffer())

            new_row = {
                "نام ابزار": name,
                "کد ابزار": code,
                "شماره قفسه": shelf,
                "مسیر عکس": img_path
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            # ذخیره در Google Sheet
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())

            st.success(f"✅ ابزار '{name}' ذخیره شد!")

# ------------------ مشاهده ابزارها ------------------
elif menu == "📋 مشاهده ابزارها":
    st.header("📋 لیست ابزارها")
    if df.empty:
        st.info("هیچ ابزاری ثبت نشده است.")
    else:
        df["کد ابزار"] = df["کد ابزار"].astype(str)
        search_code = st.text_input("🔍 جستجو بر اساس کد ابزار:")

        if search_code:
            filtered_df = df[df["کد ابزار"].str.contains(search_code, case=False, na=False)]
        else:
            filtered_df = df

        if filtered_df.empty:
            st.warning("هیچ ابزاری با این کد پیدا نشد.")
        else:
            for _, row in filtered_df.iterrows():
                st.subheader(f"{row['نام ابزار']} (کد: {row['کد ابزار']})")
                st.text(f"📦 قفسه شماره: {int(row['شماره قفسه'])}")
                if os.path.exists(row["مسیر عکس"]):
                    st.image(row["مسیر عکس"], width=200)
                st.markdown("---")
