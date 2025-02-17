from minio import Minio
import psycopg2
import requests
import os
import time
from config import DB_CONFIG, MINIO_CONFIG
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import glob
import shutil

# Connect to MinIO
minio_client = Minio(
    MINIO_CONFIG["endpoint"],
    access_key=MINIO_CONFIG["access_key"],
    secret_key=MINIO_CONFIG["secret_key"],
    secure=False
)

# Ensure temp directory exists
BASE_TEMP_DIR = os.path.abspath("D:\\team_Ginkgo\\modules\\csr_scraper\\temp")
os.makedirs(BASE_TEMP_DIR, exist_ok=True)

# Connect to the database
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

# Download PDF (prefer requests, fallback to Selenium)
def download_pdf(url, save_path):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.agilent.com/",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
    session = requests.Session()

    try:
        response = session.get(url, stream=True, timeout=15, headers=headers)
        if response.status_code == 200:
            with open(save_path, "wb") as file:
                file.write(response.content)
            print(f"{save_path} downloaded successfully (requests)")
            return True
        else:
            print(f"requests failed ({response.status_code}), trying Selenium download...")
    except Exception as e:
        print(f"requests exception: {e}, trying Selenium download...")

    return selenium_download_pdf(url, save_path)

# Download PDF using Selenium
def selenium_download_pdf(url, save_path):
    save_path = os.path.abspath(save_path)  # Ensure `save_path` is absolute path
    download_folder = os.path.dirname(save_path)
    os.makedirs(download_folder, exist_ok=True)  # Ensure `temp` directory exists

    # Configure Chrome
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Let PDF download directly instead of opening in Chrome
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_folder,  # Set default download directory
        "download.prompt_for_download": False,  # Do not prompt for download
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True  # Directly download PDF instead of opening in Chrome
    })

    # Start Chrome
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print(f"Visiting {url}")
        driver.get(url)
        driver.set_window_position(-2000, 0)
        time.sleep(5)  # Wait for PDF page to load

        # Wait for PDF to download automatically
        max_wait_time = 60  # Wait up to 60 seconds
        elapsed_time = 0
        downloaded_pdf = None

        while elapsed_time < max_wait_time:
            time.sleep(2)
            elapsed_time += 2
            # Check `download_folder` for new downloaded PDF
            pdf_files = glob.glob(os.path.join(download_folder, "*.pdf"))
            if pdf_files:
                downloaded_pdf = max(pdf_files, key=os.path.getctime)  # Find the latest PDF
                break

        driver.quit()

        if downloaded_pdf:
            # Print downloaded file name
            print(f"Downloaded file found: {downloaded_pdf}")

            # Rename to `save_path`
            shutil.move(downloaded_pdf, save_path)
            print(f"PDF downloaded successfully: {save_path}")
            return True
        else:
            print("Selenium download failed, timeout waiting for PDF file")
            return False
    except Exception as e:
        print(f"Selenium download exception: {e}")
        driver.quit()
        return False

# Upload to MinIO
def upload_to_minio(local_path, bucket_name, object_name):
    try:
        minio_client.fput_object(bucket_name, object_name, local_path)
        print(f"{object_name} uploaded successfully")
        return f"{MINIO_CONFIG['endpoint']}/{bucket_name}/{object_name}"
    except Exception as e:
        print(f"Upload failed: {e}")
        return None

# Update database `minio_path`
def update_minio_path(symbol, year, minio_path):
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE csr_reporting.csr_reports 
            SET minio_path = %s 
            WHERE symbol = %s AND report_year = %s;
        """, (minio_path, symbol, year))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"{symbol} {year} database update successful")
    except Exception as e:
        print(f"Database update failed: {e}")

# Process all unuploaded PDFs
def process_pdfs():
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    cursor.execute(
        "SELECT symbol, company_name, report_year, report_url FROM csr_reporting.csr_reports WHERE minio_path IS NULL AND report_url IS NOT NULL;")
    reports = cursor.fetchall()

    for symbol, company_name, year, report_url in reports:
        pdf_filename = f"{symbol.strip()}_{year}.pdf"
        local_pdf_path = os.path.join(BASE_TEMP_DIR, pdf_filename)  # Ensure file name is `symbol_year.pdf`

        if download_pdf(report_url, local_pdf_path):
            minio_path = upload_to_minio(local_pdf_path, MINIO_CONFIG["bucket"], pdf_filename)
            if minio_path:
                update_minio_path(symbol, year, minio_path)

            os.remove(local_pdf_path)

    cursor.close()
    conn.close()

# Run
if __name__ == "__main__":
    process_pdfs()
