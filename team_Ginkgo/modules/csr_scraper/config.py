# Google API Key
GOOGLE_API_KEY = "AIzaSyCgYeXx0D-kHYOyCz1q0xsVwWq-g5lNLtg"

# Google Custom Search Engine ID
GOOGLE_CX = "b5e302fa89034451f"

# Database Configuration
DB_CONFIG = {
    "dbname": "fift",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5439
}

# MINIO Configuration
MINIO_CONFIG = {
    "endpoint": "localhost:9000",
    "access_key": "ift_bigdata",
    "secret_key": "minio_password",
    "bucket": "csreport"
}

# KAFKA Configuration
KAFKA_CONFIG = {
    "bootstrap_servers": "localhost:9092",
    "topic": "csr_reports"
}