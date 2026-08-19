import sys
import psycopg2
import psycopg2.extras
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
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Ensure category 'AI & Machine Learning' exists
cur.execute("SELECT id FROM knowledge_categories WHERE slug = 'ai-machine-learning';")
ai_cat = cur.fetchone()
if not ai_cat:
    cur.execute("""
        INSERT INTO knowledge_categories (name, slug, description, display_order)
        VALUES ('AI & Machine Learning', 'ai-machine-learning', 'Các bài viết về Trí tuệ nhân tạo, LLMs, RAG và AI Agents.', 5)
        RETURNING id;
    """)
    ai_cat_id = cur.fetchone()['id']
else:
    ai_cat_id = ai_cat['id']

# Get existing category IDs
cur.execute("SELECT id, slug FROM knowledge_categories;")
cats_map = {row['slug']: row['id'] for row in cur.fetchall()}
print('Categories map:', cats_map)

# 2. Seed Projects
new_projects = [
    {
        'title': 'E-Commerce Microservices Platform & High-Concurrency Flash Sale',
        'technologies': 'Java 21, Spring Boot 3, Spring Cloud, Kafka, Redis, PostgreSQL, Docker, Kubernetes',
        'summary': 'Nền tảng thương mại điện tử đa kênh xử lý đơn hàng chịu tải cao trong các đợt Flash Sale với cơ chế Redis Distributed Lock và hàng đợi Kafka.',
        'description': '''<h3>1. Tổng quan dự án</h3>
<p>E-Commerce Microservices Platform là hệ thống thương mại điện tử phân tán quy mô lớn, được thiết kế để giải quyết bài toán nghẽn cổ chai và quá tải đơn hàng trong các chiến dịch Flash Sale (hàng chục nghìn lượt mua hàng đồng thời/giây).</p>
<h3>2. Kiến trúc & Công nghệ chủ đạo</h3>
<ul>
  <li><b>Microservices Architecture:</b> Tách rời các domain độc lập: <i>Product Service</i>, <i>Order Service</i>, <i>Inventory Service</i>, <i>Payment Service</i>, <i>Notification Service</i> giao tiếp qua REST API và gRPC.</li>
  <li><b>Chống Bán Quá Số Lượng (Anti-Overselling):</b> Sử dụng <b>Redis Distributed Lock (Redisson)</b> kết hợp thực thi <b>Lua Script</b> nguyên tử (Atomic Execution) để kiểm tra và trừ tồn kho trực tiếp trên RAM với độ trễ dưới 2ms.</li>
  <li><b>Event-Driven Messaging:</b> Tích hợp <b>Apache Kafka</b> để chuyển đổi quy trình thanh toán và gửi thông báo thành xử lý bất đồng bộ, giảm tải 85% cho database chính.</li>
  <li><b>Database Optimization:</b> Phân tách Read/Write Replicas cho PostgreSQL, tối ưu Connection Pool với HikariCP.</li>
  <li><b>DevOps:</b> Đóng gói container Docker, triển khai và tự động co giãn (HPA) trên Kubernetes Cluster, giám sát hiệu năng với Prometheus & Grafana.</li>
</ul>
<h3>3. Kết quả đạt được</h3>
<p>Hệ thống vượt qua bài kiểm thử tải mô phỏng với 35,000 req/s, tỷ lệ lỗi dưới 0.01%, đảm bảo tính toàn vẹn 100% cho mọi giao dịch thanh toán.</p>''',
        'image_url': '/images/projects_3d_cover.png',
        'demo_url': 'https://ecommerce-microservices-demo.vercel.app',
        'source_url': 'https://github.com/quockhoa53/ecommerce-microservices-platform',
        'featured': True,
        'display_order': 2
    },
    {
        'title': 'Enterprise AI Agent & RAG Document Intelligence Assistant',
        'technologies': 'Python, FastAPI, LangChain, Qdrant Vector DB, Llama 3, OpenAI API, React',
        'summary': 'Hệ thống trợ lý AI Agent tra cứu và trích xuất thông tin tự động từ kho tài liệu nội bộ doanh nghiệp áp dụng kỹ thuật RAG tiên tiến (Hybrid Search, Re-ranking).',
        'description': '''<h3>1. Tổng quan dự án</h3>
<p>Enterprise AI Agent là giải pháp trí tuệ nhân tạo toàn diện giúp doanh nghiệp tự động hóa việc tra cứu văn bản quy trình, hợp đồng và tài liệu kỹ thuật phức tạp thông qua giao diện hội thoại thông minh.</p>
<h3>2. Kiến trúc & Kỹ thuật AI chuyên sâu</h3>
<ul>
  <li><b>Pipeline RAG Nâng Cao (Advanced RAG):</b> Tự động đọc và bóc tách cấu trúc file PDF, DOCX, Markdown; áp dụng thuật toán <i>Recursive Semantic Chunking</i> giữ trọn vẹn ngữ nghĩa từng điều khoản.</li>
  <li><b>Hybrid Search & Re-ranking:</b> Kết hợp tìm kiếm từ khóa BM25 với tìm kiếm vector ngữ nghĩa (Vector Embeddings) trên <b>Qdrant Vector DB</b>, sau đó xếp hạng lại kết quả bằng mô hình <i>Cohere / BGE Re-ranker</i> nhằm loại bỏ hoàn toàn các thông tin gây nhiễu.</li>
  <li><b>Agentic Tool Use:</b> Sử dụng LangGraph & ReAct Pattern cho phép AI tự động kích hoạt các công cụ phân tích số liệu, xuất file Excel tóm tắt và gửi email báo cáo cho người quản trị.</li>
  <li><b>Bảo mật dữ liệu:</b> Tích hợp kiểm duyệt Prompt Injection và Guardrails bảo vệ dữ liệu nhạy cảm của doanh nghiệp.</li>
</ul>''',
        'image_url': '/images/projects_3d_cover.png',
        'demo_url': 'https://enterprise-rag-assistant.vercel.app',
        'source_url': 'https://github.com/quockhoa53/enterprise-rag-document-agent',
        'featured': True,
        'display_order': 3
    },
    {
        'title': 'Real-time IoT Telemetry & Analytics Dashboard',
        'technologies': 'Java, Spring Boot, Apache Flink, Apache Kafka, TimescaleDB, WebSockets, Chart.js',
        'summary': 'Hệ thống tiếp nhận và xử lý dữ liệu cảm biến IoT thời gian thực với hàng trăm nghìn sự kiện/giây, cảnh báo tức thời qua WebSocket.',
        'description': '''<h3>1. Tổng quan dự án</h3>
<p>Nền tảng thu thập và xử lý luồng dữ liệu thời gian thực từ mạng lưới hàng ngàn thiết bị cảm biến IoT công nghiệp, phục vụ giám sát nhiệt độ, áp suất và tình trạng vận hành của nhà máy.</p>
<h3>2. Giải pháp kỹ thuật</h3>
<ul>
  <li><b>Stream Processing:</b> Sử dụng <b>Apache Flink</b> kết hợp <b>Apache Kafka</b> để tính toán cửa sổ thời gian trượt (Tumbling & Sliding Windows), phát hiện tức thì các ngưỡng nhiệt độ bất thường trong vòng dưới 100ms.</li>
  <li><b>Lưu trữ chuỗi thời gian:</b> Sử dụng <b>TimescaleDB</b> (PostgreSQL extension) với cơ chế nén dữ liệu Hypertable giúp tiết kiệm 70% dung lượng đĩa và tối ưu truy vấn lịch sử vận hành.</li>
  <li><b>Real-time Visuals:</b> Đẩy dữ liệu cảnh báo tức thì về trình duyệt qua WebSockets / STOMP protocol.</li>
</ul>''',
        'image_url': '/images/projects_3d_cover.png',
        'demo_url': 'https://iot-telemetry-dashboard.vercel.app',
        'source_url': 'https://github.com/quockhoa53/realtime-iot-telemetry-pipeline',
        'featured': False,
        'display_order': 4
    },
    {
        'title': 'Payment Gateway & Financial Transaction Reconciliation Engine',
        'technologies': 'Java, Spring Boot, PostgreSQL, RabbitMQ, HashiCorp Vault, Prometheus, Grafana',
        'summary': 'Cổng thanh toán tích hợp VNPay, MoMo, ZaloPay và đối soát tự động hàng triệu giao dịch tài chính với cơ chế Idempotency Key và 2PC.',
        'description': '''<h3>1. Tổng quan dự án</h3>
<p>Hệ thống cổng trung gian thanh toán và đối soát tự động doanh thu định kỳ, kết nối với nhiều nhà cung cấp thanh toán (VNPay, MoMo, ZaloPay, VietQR).</p>
<h3>2. Điểm nhấn kiến trúc an toàn tài chính</h3>
<ul>
  <li><b>Idempotency Key Pattern:</b> Đảm bảo mỗi giao dịch chỉ được trừ tiền và hạch toán đúng duy nhất 1 lần, chống lỗi gửi trùng lặp (Double-charging).</li>
  <li><b>Outbox Pattern & RabbitMQ:</b> Đảm bảo tính nhất quán cuối cùng (Eventual Consistency) giữa cơ sở dữ liệu nội bộ và các cổng thanh toán bên thứ ba.</li>
  <li><b>Bảo mật chuẩn ngân hàng:</b> Mã hóa khóa bí mật bằng HashiCorp Vault, tuân thủ tiêu chuẩn bảo mật PCI-DSS, mã hóa chữ ký HMAC-SHA256.</li>
  <li><b>Đối soát tự động:</b> Hệ thống Batch Job tự động so khớp file sao kê giao dịch từ ngân hàng vào cuối ngày và gửi cảnh báo lệch dữ liệu.</li>
</ul>''',
        'image_url': '/images/projects_3d_cover.png',
        'demo_url': 'https://payment-reconciliation-engine.vercel.app',
        'source_url': 'https://github.com/quockhoa53/payment-gateway-reconciliation',
        'featured': False,
        'display_order': 5
    }
]

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'projects';")
print('Projects columns:', [c['column_name'] for c in cur.fetchall()])
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'knowledge_articles';")
print('Articles columns:', [c['column_name'] for c in cur.fetchall()])

for p in new_projects:
    cur.execute("SELECT id FROM projects WHERE title = %s;", (p['title'],))
    existing = cur.fetchone()
    if not existing:
        cur.execute("""
            INSERT INTO projects (title, description, technologies, image_url, demo_url, source_url, featured, display_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (p['title'], p['description'], p['technologies'], p['image_url'], p['demo_url'], p['source_url'], p['featured'], p['display_order']))
        print(f"Inserted project: {p['title']}")
    else:
        cur.execute("""
            UPDATE projects SET description = %s, technologies = %s, demo_url = %s, source_url = %s, featured = %s, display_order = %s
            WHERE id = %s;
        """, (p['description'], p['technologies'], p['demo_url'], p['source_url'], p['featured'], p['display_order'], existing['id']))
        print(f"Updated project: {p['title']}")

# 3. Seed Knowledge Articles across all categories
new_articles = [
    {
        'category_slug': 'database-data',
        'title': 'Chiến lược Caching đa tầng với Redis: Từ Cache-Aside đến xử lý Cache Avalanche & Stampede',
        'slug': 'chien-luoc-caching-da-tang-voi-redis',
        'summary': 'Phân tích các mô hình caching phổ biến (Cache-Aside, Write-Through, Write-Back) và giải pháp xử lý triệt để các sự cố kinh điển: Cache Avalanche, Cache Breakdown và Cache Stampede trong hệ thống lớn.',
        'content': '''<h3>1. Tại sao Caching lại là chìa khóa hiệu năng Backend?</h3>
<p>Trong các hệ thống có lượng truy cập lớn, Database luôn là tài nguyên chịu tải nặng nhất do chi phí đọc ghi đĩa và xử lý quan hệ phức tạp. Áp dụng Caching với Redis giúp đưa thời gian phản hồi từ hàng chục miligiây xuống chỉ dưới 1 miligiây.</p>
<h3>2. Các mô hình Caching phổ biến</h3>
<ul>
  <li><b>Cache-Aside (Lazy Loading):</b> Ứng dụng đọc từ cache trước, nếu cache miss thì đọc từ DB rồi ghi ngược lại vào Cache. Đây là mô hình linh hoạt và phổ biến nhất.</li>
  <li><b>Write-Through:</b> Ghi dữ liệu đồng thời vào Cache và Database trong cùng một transaction. Đảm bảo tính nhất quán cao nhưng tăng độ trễ khi ghi.</li>
  <li><b>Write-Behind (Write-Back):</b> Ghi vào Cache trước và phản hồi ngay lập tức, sau đó luồng nền sẽ gom batch ghi vào Database. Cho tốc độ ghi cực nhanh nhưng có nguy cơ mất mát dữ liệu nếu cache gặp sự cố.</li>
</ul>
<h3>3. Xử lý các sự cố Caching kinh điển</h3>
<ul>
  <li><b>Cache Avalanche (Tuyết lở):</b> Hàng loạt key quan trọng hết hạn cùng một thời điểm khiến mọi request tràn thẳng vào Database. <i>Giải pháp:</i> Thêm một khoảng thời gian ngẫu nhiên (Jitter) vào TTL của từng key (ví dụ: TTL = 30 phút + random(0-300s)).</li>
  <li><b>Cache Breakdown (Điểm nóng hết hạn):</b> Một key có lượt truy cập cực khủng (Hot Key) vừa hết hạn, hàng ngàn request đồng thời truy vấn DB để tính toán lại. <i>Giải pháp:</i> Áp dụng <b>Mutex Lock / Distributed Lock</b> với Redis để chỉ cho phép 1 request duy nhất được truy vấn DB và tái tạo cache.</li>
  <li><b>Cache Penetration:</b> Request truy vấn các dữ liệu hoàn toàn không tồn tại khiến cache luôn miss. <i>Giải pháp:</i> Sử dụng <b>Bloom Filter</b> ở tầng trước cache hoặc lưu cache giá trị Null với TTL ngắn.</li>
</ul>''',
        'featured': True
    },
    {
        'category_slug': 'database-data',
        'title': 'Đánh chỉ mục Index B-Tree và GIN trong PostgreSQL: Tối ưu câu truy vấn từ 2 giây xuống dưới 5ms',
        'slug': 'danh-chi-muc-index-b-tree-va-gin-trong-postgresql',
        'summary': 'Hướng dẫn chi tiết cách đọc Explain Analyze, lựa chọn loại Index phù hợp (B-Tree, GIN, Partial Index, Composite Index) và những cạm bẫy khiến Index bị vô hiệu hóa.',
        'content': '''<h3>1. Đọc hiểu Execution Plan với EXPLAIN ANALYZE</h3>
<p>Để tối ưu một câu lệnh SQL chậm, bước đầu tiên luôn là chạy <code>EXPLAIN (ANALYZE, BUFFERS)</code> để xem PostgreSQL đang thực thi theo phương pháp nào: <b>Seq Scan</b> (quét toàn bộ bảng) hay <b>Index Scan / Bitmap Index Scan</b> (sử dụng chỉ mục).</p>
<h3>2. Các loại Index quan trọng trong PostgreSQL</h3>
<ul>
  <li><b>B-Tree Index:</b> Loại index mặc định và mạnh mẽ nhất cho các phép so sánh bằng (=), lớn hơn/nhỏ hơn (<, >, <=, >=), khoảng (BETWEEN) và sắp xếp (ORDER BY).</li>
  <li><b>GIN Index (Generalized Inverted Index):</b> Cực kỳ tối ưu cho các kiểu dữ liệu mảng (Arrays), tìm kiếm toàn văn bản (Full-text Search), và đặc biệt là kiểu dữ liệu <b>JSONB</b>.</li>
  <li><b>Partial Index (Index có điều kiện):</b> Chỉ đánh index trên một tập con dữ liệu (ví dụ: <code>WHERE status = 'ACTIVE'</code>), giúp giảm 80% kích thước file index và tăng tốc độ ghi dữ liệu.</li>
  <li><b>Covering Index (INCLUDE Clause):</b> Đính kèm các cột phụ vào index bằng mệnh đề <code>INCLUDE</code> để PostgreSQL thực hiện <b>Index Only Scan</b> mà không cần truy xuất lại Heap page.</li>
</ul>
<h3>3. Những cạm bẫy phổ biến làm vô hiệu hóa Index</h3>
<ul>
  <li>Sử dụng hàm trên cột có index (ví dụ: <code>WHERE LOWER(email) = '...'</code> làm mất index, cần dùng Expression Index <code>CREATE INDEX ON profiles (LOWER(email))</code>).</li>
  <li>Sử dụng toán tử LIKE với ký tự đại diện ở đầu: <code>LIKE '%khoa'</code>.</li>
  <li>Không duy trì lệnh <code>ANALYZE</code> định kỳ khiến PostgreSQL Query Planner ước lượng sai số lượng bản ghi (Cost estimation).</li>
</ul>''',
        'featured': False
    },
    {
        'category_slug': 'java-spring-boot',
        'title': 'Tối ưu hiệu năng ứng dụng Spring Boot: Virtual Threads (Project Loom), HikariCP và JVM Tuning',
        'slug': 'toi-uu-hieu-nang-spring-boot-virtual-threads-hikaricp',
        'summary': 'Khai thác sức mạnh của Java 21 Virtual Threads trong Spring Boot 3, cấu hình tối ưu Connection Pool HikariCP và tinh chỉnh JVM Garbage Collection cho môi trường chịu tải cao.',
        'content': '''<h3>1. Kỷ nguyên Virtual Threads với Java 21 & Spring Boot 3</h3>
<p>Trước Java 21, mô hình một thread tương ứng một OS Thread (Platform Thread) tốn khoảng 1MB bộ nhớ RAM và chi phí Context Switching của hệ điều hành rất đắt đỏ. Với <b>Virtual Threads (Project Loom)</b>, hàng triệu lightweight threads có thể chạy đồng thời, tự động nhả OS carrier thread khi gặp tác vụ I/O chặn (Blocking I/O).</p>
<p>Để kích hoạt trong Spring Boot 3:</p>
<pre><code>spring.threads.virtual.enabled=true</code></pre>
<h3>2. Tối ưu Connection Pool với HikariCP</h3>
<p>Một sai lầm kinh điển là cấu hình `maximum-pool-size` quá lớn (ví dụ: 100 hay 200). Theo công thức của các kỹ sư PostgreSQL và HikariCP:</p>
<pre><code>connections = ((core_count * 2) + effective_spindle_count)</code></pre>
<p>Với server 4 cores CPU, pool size chỉ cần đặt từ 10 đến 20 là đủ để đạt thông lượng tối đa mà không gây nghẽn CPU và lock contention tại Database.</p>
<h3>3. Tinh chỉnh Garbage Collection (GC Tuning)</h3>
<p>Với các microservices hiện đại, chuyển đổi sang <b>G1GC</b> hoặc <b>ZGC (Z Garbage Collector)</b> trên Java 21 giúp giảm thời gian dừng hệ thống (Stop-the-world Pause Time) xuống dưới 1 miligiây, mang lại trải nghiệm mượt mà cho người dùng cuối.</p>''',
        'featured': True
    },
    {
        'category_slug': 'java-spring-boot',
        'title': 'Xử lý Bất đồng bộ và Luồng sự kiện Event-Driven với Spring Boot & Apache Kafka',
        'slug': 'xu-ly-bat-dong-bo-event-driven-spring-boot-kafka',
        'summary': 'Thiết kế kiến trúc hướng sự kiện (EDA) với Kafka trong Spring Boot, xử lý bài toán Dead Letter Queue (DLQ), Consumer Idempotency và bảo đảm thứ tự tin nhắn (Partition Key).',
        'content': '''<h3>1. Chuyển đổi từ Monolith đồng bộ sang Event-Driven Architecture</h3>
<p>Giao tiếp đồng bộ (HTTP REST giữa các service) tạo ra sự phụ thuộc chặt chẽ (Tight Coupling) và rủi ro Cascading Failure: Nếu Service B chậm, Service A sẽ bị nghẽn toàn bộ luồng xử lý. Với Apache Kafka, các service giao tiếp qua các sự kiện bất đồng bộ (Domain Events), giúp hệ thống đạt tính độc lập cao và khả năng mở rộng vượt trội.</p>
<h3>2. Đảm bảo thứ tự tin nhắn (Message Ordering)</h3>
<p>Kafka bảo đảm thứ tự tin nhắn theo từng Partition. Bằng cách chỉ định <b>Partition Key</b> phù hợp (ví dụ: <code>order_id</code> hoặc <code>user_id</code>), tất cả sự kiện liên quan đến cùng một đơn hàng sẽ luôn đi vào cùng 1 partition và được xử lý tuần tự chính xác.</p>
<h3>3. Xử lý lỗi với Dead Letter Queue (DLQ) & Retry Mechanism</h3>
<p>Khi Consumer gặp lỗi xử lý dữ liệu (ví dụ: định dạng sai hoặc dịch vụ bên thứ ba bị lỗi), hệ thống không nên để tắc nghẽn toàn bộ luồng. Thiết lập <b>Retry Topic</b> với khoảng thời gian dãn cách (Backoff Exponential) và tự động đẩy các tin nhắn lỗi quá số lần quy định sang <b>Dead Letter Topic (DLT)</b> để đội ngũ kỹ thuật phân tích và khắc phục.</p>''',
        'featured': False
    },
    {
        'category_slug': 'ai-machine-learning',
        'title': 'Xây dựng hệ thống RAG nâng cao (Advanced RAG): Hybrid Search, Re-ranking và Context Compression',
        'slug': 'xay-dung-he-thong-rag-nang-cao-advanced-rag',
        'summary': 'Giải quyết bài toán ảo giác (Hallucination) của LLMs bằng kiến trúc Advanced RAG: Kết hợp Vector Search và BM25, lọc nhiễu với Cohere Re-ranker và nén ngữ cảnh trước khi sinh câu trả lời.',
        'content': '''<h3>1. Giới hạn của Naive RAG (RAG truyền thống)</h3>
<p>Naive RAG chỉ đơn giản là: Cắt nhỏ tài liệu (Chunking) -> Tạo Vector Embedding -> Truy vấn Top-K tương đồng nhất (Cosine Similarity) -> Nhồi vào Prompt của LLM. Cách làm này thường gặp các hạn chế lớn:</p>
<ul>
  <li>Mất mát ngữ cảnh do chia đoạn cắt ngang câu.</li>
  <li>Chỉ tìm kiếm ngữ nghĩa nên dễ bỏ sót các từ khóa chuyên ngành chính xác (mã sản phẩm, tên hàm, số hiệu điều khoản).</li>
  <li>Các đoạn văn bản tương đồng cao chưa chắc đã chứa câu trả lời đúng cho câu hỏi của người dùng.</li>
</ul>
<h3>2. Kiến trúc Advanced RAG tối ưu</h3>
<ul>
  <li><b>Hybrid Search:</b> Kết hợp tìm kiếm từ khóa dày dặn (Dense Retrieval qua Vector DB) với tìm kiếm từ khóa thưa (Sparse Retrieval qua BM25/Elasticsearch) theo thuật toán <i>Reciprocal Rank Fusion (RRF)</i>.</li>
  <li><b>Cross-Encoder Re-ranking:</b> Sau khi lấy ra Top 20 đoạn văn bản tiềm năng, sử dụng mô hình Re-ranker (như BGE-Reranker hoặc Cohere) để chấm điểm chính xác mức độ liên quan thực tế giữa câu hỏi và từng đoạn văn, lấy ra Top 3-5 đoạn xuất sắc nhất.</li>
  <li><b>Context Compression:</b> Trích xuất chỉ các câu văn cốt lõi chứa thông tin giải đáp, loại bỏ hoàn toàn các câu thừa trước khi đưa vào LLM Context Window, giúp giảm 60% chi phí token và loại bỏ 95% ảo giác.</li>
</ul>''',
        'featured': True
    },
    {
        'category_slug': 'ai-machine-learning',
        'title': 'Thiết kế AI Agent tự động hóa tác vụ: Phân biệt ReAct Pattern, Function Calling và Plan-and-Solve',
        'slug': 'thiet-ke-ai-agent-tu-dong-hoa-tac-vu',
        'summary': 'Phân tích nguyên lý hoạt động của các AI Agent thông minh: Cách thức Agent suy luận (Reasoning), lập kế hoạch (Planning), sử dụng công cụ (Tool Execution) và quản lý bộ nhớ dài hạn.',
        'content': '''<h3>1. AI Agent khác gì so với một Chatbot thông thường?</h3>
<p>Một Chatbot thông thường chỉ tiếp nhận văn bản và sinh ra văn bản tiếp theo dựa trên dữ liệu tĩnh. Trong khi đó, một <b>AI Agent</b> sở hữu các năng lực vượt trội:</p>
<ul>
  <li><b>Tự chủ (Autonomy):</b> Tự phân tích mục tiêu của người dùng và chia nhỏ thành các bước hành động cụ thể.</li>
  <li><b>Sử dụng công cụ (Tool Use / Function Calling):</b> Có thể gọi API, truy vấn cơ sở dữ liệu, chạy mã Python hoặc tìm kiếm web để thu thập thông tin thực tế.</li>
  <li><b>Vòng lặp quan sát & phản hồi (Reasoning Loop):</b> Quan sát kết quả từ công cụ và tự điều chỉnh hướng giải quyết nếu gặp lỗi.</li>
</ul>
<h3>2. Các kiến trúc Agent phổ biến</h3>
<ul>
  <li><b>ReAct Pattern (Reason + Act):</b> Mô hình liên tục lặp qua 3 trạng thái: <i>Suy nghĩ (Thought)</i> -> <i>Hành động (Action)</i> -> <i>Quan sát kết quả (Observation)</i> cho đến khi hoàn thành mục tiêu.</li>
  <li><b>Plan-and-Solve:</b> Agent lập toàn bộ kế hoạch từng bước trước khi bắt đầu thực thi, phù hợp cho các bài toán phức tạp đòi hỏi nhiều bước tính toán logic có thứ tự.</li>
</ul>''',
        'featured': False
    },
    {
        'category_slug': 'devops-engineering',
        'title': 'Triển khai CI/CD tự động với GitHub Actions, Docker Container và Kubernetes (K8s)',
        'slug': 'trien-khai-cicd-tu-dong-github-actions-docker-k8s',
        'summary': 'Hướng dẫn xây dựng tuyến pipeline CI/CD hoàn chỉnh: Tự động chạy unit test, build Multi-stage Docker Image, quét lỗ hổng bảo mật và triển khai Zero-downtime trên Kubernetes.',
        'content': '''<h3>1. Tầm quan trọng của tự động hóa triển khai</h3>
<p>Triển khai thủ công (Manual Deployment) qua FTP hoặc SSH là nguyên nhân hàng đầu gây ra lỗi hệ thống và gián đoạn dịch vụ. Xây dựng tuyến CI/CD tự động đảm bảo mọi dòng code đưa lên production đều đã vượt qua toàn bộ quy trình kiểm thử và đánh giá bảo mật nghiêm ngặt.</p>
<h3>2. Tối ưu Dockerfile với Multi-Stage Build</h3>
<p>Thay vì đóng gói toàn bộ JDK và Gradle vào image cuối cùng (dung lượng trên 800MB), sử dụng <b>Multi-Stage Build</b> cho phép chúng ta compile code ở stage 1 và chỉ sao chép file `.jar` sang stage 2 chạy trên nền <b>Eclipse Temurin JRE Alpine</b> siêu nhẹ (dung lượng chỉ ~ 120MB), tăng tốc độ pull image và giảm thiểu bề mặt tấn công.</p>
<h3>3. Chiến lược Zero-Downtime Deployment trên Kubernetes</h3>
<p>Sử dụng <b>Rolling Update</b> kết hợp với cấu hình <b>Readiness & Liveness Probes</b> chính xác giúp Kubernetes đảm bảo pod mới đã hoàn toàn sẵn sàng tiếp nhận request (warm-up) trước khi hủy pod cũ, bảo đảm trải nghiệm không bị gián đoạn cho người dùng.</p>''',
        'featured': False
    },
    {
        'category_slug': 'architecture',
        'title': 'Thiết kế hệ thống chịu tải cao (High Concurrency System Design): Rate Limiting, Circuit Breaker và Bulkhead',
        'slug': 'thiet-ke-he-thong-chiu-tai-cao-rate-limiting-circuit-breaker',
        'summary': 'Tổng hợp các mẫu thiết kế bảo vệ hệ thống phân tán khỏi quá tải: Token Bucket Rate Limiting, Resilience4j Circuit Breaker và Bulkhead Pattern chống sụp đổ dây chuyền.',
        'content': '''<h3>1. Những thách thức khi hệ thống chịu tải đột biến</h3>
<p>Khi lượng truy cập tăng vọt gấp hàng chục lần, nếu không có các cơ chế tự vệ, hệ thống sẽ gặp hiện tượng <b>Cascading Failure (Sụp đổ dây chuyền)</b>: Một service bị nghẽn sẽ giữ connection của các service gọi nó, dẫn đến toàn bộ hệ thống bị cạn kiệt tài nguyên RAM và CPU.</p>
<h3>2. Các mẫu thiết kế tự vệ cốt lõi</h3>
<ul>
  <li><b>Rate Limiting (Giới hạn tốc độ):</b> Sử dụng thuật toán <i>Token Bucket</i> hoặc <i>Leaky Bucket</i> để giới hạn số lượng request từ mỗi IP hoặc User ID trong một khung thời gian, chặn đứng các cuộc tấn công DoS hoặc crawler trái phép.</li>
  <li><b>Circuit Breaker (Cầu dao ngắt mạch):</b> Sử dụng <b>Resilience4j</b> để theo dõi tỷ lệ lỗi của dịch vụ phụ thuộc. Khi tỷ lệ lỗi vượt quá ngưỡng (ví dụ 50%), cầu dao sẽ mở (OPEN) và phản hồi ngay lập tức bằng dữ liệu dự phòng (Fallback response) thay vì tiếp tục gửi request vào service đang chết.</li>
  <li><b>Bulkhead Pattern:</b> Chia nhỏ thread pool và tài nguyên riêng biệt cho từng service trọng yếu, đảm bảo nếu một tính năng phụ gặp sự cố thì các luồng thanh toán và đăng nhập chính vẫn hoạt động bình thường.</li>
</ul>''',
        'featured': True
    }
]

for a in new_articles:
    cat_id = cats_map.get(a['category_slug'])
    if not cat_id:
        cat_id = cats_map.get('architecture', 1)
    
    cur.execute("SELECT id FROM knowledge_articles WHERE slug = %s;", (a['slug'],))
    existing = cur.fetchone()
    if not existing:
        cur.execute("""
            INSERT INTO knowledge_articles (
                category_id, title, slug, summary, content, thumbnail_url, status, featured, view_count, published_at, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, '/images/projects_3d_cover.png', 'PUBLISHED', %s, 0, NOW(), NOW(), NOW()
            );
        """, (cat_id, a['title'], a['slug'], a['summary'], a['content'], a['featured']))
        print(f"Inserted article: {a['title']}")
    else:
        cur.execute("""
            UPDATE knowledge_articles SET 
                category_id = %s, title = %s, summary = %s, content = %s, featured = %s, status = 'PUBLISHED', updated_at = NOW()
            WHERE id = %s;
        """, (cat_id, a['title'], a['summary'], a['content'], a['featured'], existing['id']))
        print(f"Updated article: {a['title']}")

print('=== ALL DIVERSE PROJECTS AND KNOWLEDGE ARTICLES SEEDED SUCCESSFULLY! ===')
