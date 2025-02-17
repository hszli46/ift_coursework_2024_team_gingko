import psycopg2
from config import DB_CONFIG

def insert_top_5_companies():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Select the top 5 companies (column name `security` corresponds to company name)
    cursor.execute("""
        SELECT symbol, security FROM csr_reporting.company_static
        ORDER BY symbol
        LIMIT 5;
    """)
    top_5_companies = cursor.fetchall()

    for symbol, security in top_5_companies:
        cursor.execute("""
            INSERT INTO csr_reporting.csr_reports (symbol, company_name, report_year)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (symbol, security, 2023))

    conn.commit()
    cursor.close()
    conn.close()
    print("Successfully inserted top 5 companies into csr_reports")

if __name__ == "__main__":
    insert_top_5_companies()

