# app.py
import streamlit as st
import pandas as pd
import os
import json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ------------------ تنظیمات صفحه ------------------
st.set_page_config(page_title="مدیریت ابزارها", page_icon="🧰")
st.title("📦 مدیریت ابزارها")
st.info("در حال اتصال به Google Drive...")

# ------------------ احراز هویت با Service Account ------------------
try:
    if "google" not in st.secrets or "client_config" not in st.secrets["google"]:
        st.error("❌ تنظیمات Google در secrets.toml یافت نشد. لطفاً مقدار client_config را اضافه کن.")
        st.stop()

    # خواندن داده‌ها از secrets و ذخیره به فایل موقت JSON
    creds_json = json.loads(st.secrets["google"]["client_config"])
    with open("service_account.json", "w") as f:
        json.dump(creds_json, f)

    # پیکربندی GoogleAuth برای استفاده از Service Account
    gauth = GoogleAuth()
    gauth.LoadServiceConfigSettings = lambda: None  # جلوگیری از تنظیمات پیش‌فرض
    gauth.ServiceAuth()  # با کلید Service Account لاگین می‌کند

    drive = GoogleDrive(gauth)
    st.success("✅ اتصال به Google Drive برقرار شد!")

except Exception as e:
    st.error(f"❌ خطا در احراز هویت Google Drive: {e}")
    st.stop()

# ------------------ مسیر فایل‌ها ------------------
DATA_FILE = "tools_data.csv"
IMAGES_DIR = "tool_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# ------------------ پوشه مخصوص در Google Drive ------------------
FOLDER_NAME = "ToolManager_Data"

try:
    folders = drive.ListFile({
        'q': f"title='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if folders:
        folder_id = folders[0]['id']
    else:
        folder_metadata = {'title': FOLDER_NAME, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        folder_id = folder['id']
except Exception as e:
    st.error(f"⚠️ خطا در بررسی پوشه Google Drive: {e}")
    st.stop()

# ------------------ دانلود فایل CSV از Drive ------------------
try:
    file_list = drive.ListFile({
        'q': f"title='tools_data.csv' and '{folder_id}' in parents and trashed=false"
    }).GetList()
    if file_list:
        file_id = file_list[0]['id']
        downloaded = drive.CreateFile({'id': file_id})
        downloaded.GetContentFile(DATA_FILE)
        st.success("📥 داده‌ها از Google Drive بارگذاری شدند.")
    else:
        st.info("هیچ فایل داده‌ای در Drive پیدا نشد. (اولین اجرا)")
except Exception as e:
    st.warning(f"⚠️ خطا در بارگذاری داده‌ها: {e}")

# ------------------ بارگذاری داده‌ها ------------------
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["نام ابزار", "کد ابزار", "شماره قفسه", "مسیر عکس"])

# ------------------ منوی اصلی ------------------
menu = st.sidebar.selectbox("📂 انتخاب صفحه", ["➕ افزودن ابزار", "📋 مشاهده ابزارها"])

# ------------------ افزودن ابزار ------------------
if menu == "➕ افزودن ابزار":
    st.header("➕ افزودن ابزار جدید")

    name = st.selectbox("نام ابزار:", ["تپه", "بنوک", "چکش", "انبردست"])
    code = st.text_input("کد ابزار:")
    shelf = st.number_input("شماره قفسه:", min_value=1, step=1)
    image_file = st.file_uploader("📸 انتخاب عکس ابزار", type=["jpg", "png", "jpeg"])

    if st.button("💾 ذخیره ابزار"):
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
            df.to_csv(DATA_FILE, index=False)

            try:
                # آپلود CSV به Drive
                file_list = drive.ListFile({'q': f"title='tools_data.csv' and '{folder_id}' in parents and trashed=false"}).GetList()
                if file_list:
                    file_csv = file_list[0]
                else:
                    file_csv = drive.CreateFile({'title': 'tools_data.csv', 'parents': [{'id': folder_id}]})
                file_csv.SetContentFile(DATA_FILE)
                file_csv.Upload()

                # آپلود عکس
                img_drive = drive.CreateFile({'title': os.path.basename(img_path), 'parents': [{'id': folder_id}]})
                img_drive.SetContentFile(img_path)
                img_drive.Upload()

                st.success(f"✅ ابزار '{name}' ذخیره و در Google Drive آپلود شد!")

            except Exception as e:
                st.error(f"❌ خطا در آپلود فایل‌ها به Drive: {e}")

        else:
            st.warning("⚠️ لطفاً تمام فیلدها را پر کنید.")

# ------------------ مشاهده ابزارها ------------------
elif menu == "📋 مشاهده ابزارها":
    st.header("📋 لیست ابزارها")

    if len(df) == 0:
        st.info("هیچ ابزاری ثبت نشده است.")
    else:
        search_code = st.text_input("🔍 جستجو بر اساس کد ابزار:")

        if search_code:
            filtered_df = df[df["کد ابزار"].astype(str).str.contains(search_code, case=False, na=False)]
        else:
            filtered_df = df

        if len(filtered_df) == 0:
            st.warning("هیچ ابزاری با این کد پیدا نشد.")
        else:
            for _, row in filtered_df.iterrows():
                st.subheader(f"{row['نام ابزار']} (کد: {row['کد ابزار']})")
                st.text(f"📦 قفسه شماره: {int(row['شماره قفسه'])}")
                if os.path.exists(row["مسیر عکس"]):
                    st.image(row["مسیر عکس"], width=200)
                st.markdown("---")
