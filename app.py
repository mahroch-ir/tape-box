import streamlit as st
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import json
import tempfile
import io
import os

# ------------------ تنظیمات صفحه ------------------
st.set_page_config(page_title="مدیریت ابزارها", page_icon="🧰")
st.title("📦 مدیریت ابزارها")
st.info("در حال اتصال به Google Drive...")

# ------------------ احراز هویت با Service Account ------------------
try:
    if "google" not in st.secrets or "client_config" not in st.secrets["google"]:
        st.error("❌ تنظیمات Google در secrets پیدا نشد. لطفاً client_config را اضافه کنید.")
        st.stop()

    # خواندن JSON از secrets
    creds_json = json.loads(st.secrets["google"]["client_config"])

    # ذخیره موقت JSON به فایل
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(creds_json, f)
        service_file = f.name

    # پیکربندی GoogleAuth
    gauth = GoogleAuth()
    gauth.LoadServiceConfigSettings = lambda: None
    gauth.settings['client_config_file'] = service_file
    gauth.ServiceAuth()

    drive = GoogleDrive(gauth)
    st.success("✅ اتصال به Google Drive برقرار شد!")

except Exception as e:
    st.error(f"❌ خطا در احراز هویت Google Drive: {e}")
    st.stop()

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
    st.error(f"⚠️ خطا در بررسی/ایجاد پوشه Google Drive: {e}")
    st.stop()

# ------------------ دانلود فایل CSV از Drive ------------------
DATA_FILE = "tools_data.csv"
try:
    file_list = drive.ListFile({
        'q': f"title='{DATA_FILE}' and '{folder_id}' in parents and trashed=false"
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
try:
    df = pd.read_csv(DATA_FILE)
except:
    df = pd.DataFrame(columns=["نام ابزار", "کد ابزار", "شماره قفسه", "GoogleDrive_ID"])

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
            try:
                # ------------------ آپلود عکس به Drive ------------------
                img_drive = drive.CreateFile({
                    'title': f"{code}_{image_file.name}",
                    'parents': [{'id': folder_id}]
                })
                img_drive.content = io.BytesIO(image_file.getvalue())
                img_drive.Upload()

                # ------------------ افزودن ردیف به DataFrame ------------------
                new_row = {
                    "نام ابزار": name,
                    "کد ابزار": code,
                    "شماره قفسه": shelf,
                    "GoogleDrive_ID": img_drive['id']
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                # ------------------ ذخیره CSV در Drive ------------------
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_drive_list = drive.ListFile({
                    'q': f"title='{DATA_FILE}' and '{folder_id}' in parents and trashed=false"
                }).GetList()
                if csv_drive_list:
                    csv_file = csv_drive_list[0]
                else:
                    csv_file = drive.CreateFile({'title': DATA_FILE, 'parents': [{'id': folder_id}]})
                csv_file.SetContentString(csv_buffer.getvalue())
                csv_file.Upload()

                st.success(f"✅ ابزار '{name}' ذخیره و در Google Drive آپلود شد!")

            except Exception as e:
                st.error(f"❌ خطا در آپلود فایل‌ها به Drive: {e}")

        else:
            st.warning("⚠️ لطفاً تمام فیلدها را پر کنید.")

# ------------------ مشاهده ابزارها ------------------
elif menu == "📋 مشاهده ابزارها":
    st.header("📋 لیست ابزارها")

    if df.empty:
        st.info("هیچ ابزاری ثبت نشده است.")
    else:
        search_code = st.text_input("🔍 جستجو بر اساس کد ابزار:")

        if search_code:
            filtered_df = df[df["کد ابزار"].astype(str).str.contains(search_code, case=False, na=False)]
        else:
            filtered_df = df

        if filtered_df.empty:
            st.warning("هیچ ابزاری با این کد پیدا نشد.")
        else:
            for _, row in filtered_df.iterrows():
                st.subheader(f"{row['نام ابزار']} (کد: {row['کد ابزار']})")
                st.text(f"📦 قفسه شماره: {int(row['شماره قفسه'])}")

                # نمایش عکس از Google Drive
                if row["GoogleDrive_ID"]:
                    file_drive = drive.CreateFile({'id': row["GoogleDrive_ID"]})
                    temp_path = f"temp_{row['کد ابزار']}.png"
                    file_drive.GetContentFile(temp_path)
                    st.image(temp_path, width=200)
                    os.remove(temp_path)

                st.markdown("---")
