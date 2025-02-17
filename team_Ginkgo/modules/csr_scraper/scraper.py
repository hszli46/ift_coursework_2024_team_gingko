import psycopg2
from googleapiclient.discovery import build
from config import DB_CONFIG, GOOGLE_API_KEY, GOOGLE_CX

# Connect to the database
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Database connection successful")
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

# Use Google API to search for PDF reports
def google_search_pdf(company_name, year):
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    query = f"{company_name} CSR report {year} filetype:pdf"

    try:
        res = service.cse().list(q=query, cx=GOOGLE_CX).execute()
        pdf_links = [item['link'] for item in res.get('items', []) if item['link'].endswith('.pdf')]
        return pdf_links[0] if pdf_links else None
    except Exception as e:
        print(f"{company_name} {year} search failed: {e}")
        return None

# Scrape and update the database
def update_csr_reports():
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()

    # Query `csr_reports` where `report_url IS NULL`
    cursor.execute("SELECT symbol, company_name, report_year FROM csr_reporting.csr_reports WHERE report_url IS NULL;")
    companies = cursor.fetchall()

    for symbol, company_name, report_year in companies:
        pdf_url = google_search_pdf(company_name, report_year)
        if pdf_url:
            cursor.execute("UPDATE csr_reporting.csr_reports SET report_url = %s WHERE symbol = %s AND report_year = %s;",
                           (pdf_url, symbol, report_year))
            conn.commit()
            print(f"{company_name} {report_year} updated: {pdf_url}")
        else:
            print(f"{company_name} {report_year} report not found")

    cursor.close()
    conn.close()
    print("All scraping tasks completed")

# Run the scraper
if __name__ == "__main__":
    update_csr_reports()
