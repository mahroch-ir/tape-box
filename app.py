import streamlit as st
import pandas as pd
from PIL import Image
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ------------------ تنظیمات صفحه ------------------
st.set_page_config(page_title="مدیریت ابزارها", page_icon="🧰")
st.title("📦 مدیریت ابزارها")

# ------------------ مسیر فایل‌ها ------------------
DATA_FILE = "tools_data.csv"
IMAGES_DIR = "tool_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# ------------------ اتصال به Google Drive ------------------
st.info("در حال برقراری ارتباط با Google Drive...")

gauth = GoogleAuth()
gauth.LoadClientConfigFile("client_secrets.json")

TOKEN_FILE = "mycreds.json"
if os.path.exists(TOKEN_FILE):
    gauth.LoadCredentialsFile(TOKEN_FILE)
    if gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
else:
    gauth.LocalWebserverAuth()
    gauth.SaveCredentialsFile(TOKEN_FILE)

drive = GoogleDrive(gauth)

# ------------------ دانلود فایل CSV از Drive ------------------
try:
    file_list = drive.ListFile({'q': "title='tools_data.csv'"}).GetList()
    if file_list:
        file_id = file_list[0]['id']
        downloaded = drive.CreateFile({'id': file_id})
        downloaded.GetContentFile(DATA_FILE)
        st.success("📥 فایل داده‌ها از Google Drive بارگذاری شد.")
except Exception:
    st.warning("⚠️ هنوز فایلی در Google Drive وجود ندارد. (اولین اجرا)")

# ------------------ بارگذاری داده‌ها ------------------
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
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

            # افزودن داده به CSV
            new_row = {
                "نام ابزار": name,
                "کد ابزار": code,
                "شماره قفسه": shelf,
                "مسیر عکس": img_path
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)

            # آپلود فایل CSV در Drive
            file_csv = drive.CreateFile({'title': 'tools_data.csv'})
            file_csv.SetContentFile(DATA_FILE)
            file_csv.Upload()

            # آپلود عکس در Drive
            img_drive = drive.CreateFile({'title': os.path.basename(img_path)})
            img_drive.SetContentFile(img_path)
            img_drive.Upload()

            st.success(f"✅ ابزار '{name}' ذخیره و در Google Drive آپلود شد!")
        else:
            st.warning("⚠️ لطفاً تمام فیلدها را پر کنید.")

# ------------------ مشاهده ابزارها ------------------
elif menu == "📋 مشاهده ابزارها":
    st.header("📋 لیست ابزارها")

    if len(df) == 0:
        st.info("هیچ ابزاری ثبت نشده است.")
    else:
        df["کد ابزار"] = df["کد ابزار"].astype(str)
        search_code = st.text_input("🔍 جستجو بر اساس کد ابزار:")

        if search_code:
            filtered_df = df[df["کد ابزار"].str.contains(search_code, case=False, na=False)]
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
