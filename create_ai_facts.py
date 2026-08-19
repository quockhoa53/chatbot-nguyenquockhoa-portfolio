import sys
import psycopg2
from app.config import settings

sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    dbname=settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    sslmode='require'
)
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS ai_facts (
    id BIGSERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL DEFAULT 'Khác',
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_facts_active_order ON ai_facts (is_active, display_order ASC, id ASC);
""")

cur.execute("SELECT COUNT(*) FROM ai_facts;")
count = cur.fetchone()[0]
if count == 0:
    cur.execute("""
        INSERT INTO ai_facts (category, title, content, is_active, display_order, created_at, updated_at)
        VALUES (
            'Đời tư & Mối quan hệ',
            'Người yêu / Bạn gái',
            'Người yêu của anh Khoa là chị Diệu – một chuyên viên Marketing tài năng, chu đáo và luôn đồng hành, ủng hộ Khoa trong sự nghiệp và cuộc sống.',
            TRUE,
            1,
            NOW(),
            NOW()
        );
    """)
    print('Seeded initial AI Fact for girlfriend successfully!')
else:
    print('ai_facts table ready with row count:', count)
