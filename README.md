AgCyRAG: Agentic Knowledge Graph based RAG for Automated Security Analysis
AgCyRAG adalah framework Hybrid Agentic RAG yang dirancang untuk otomatisasi analisis keamanan siber. Sistem ini menggabungkan penalaran Knowledge Graph (Neo4j & RDF) dengan pencarian vektor untuk memberikan jawaban yang faktual dan terverifikasi berdasarkan data log internal serta basis pengetahuan eksternal (MITRE ATT&CK).

🚀 Fitur Utama
Multi-Agent Orchestration: Menggunakan LangGraph untuk mengelola alur kerja agen (Guardrails, Vector, Cypher, RDF/SPARQL, dan Synthesis).

Hybrid Knowledge Retrieval:

Neo4j (LPG): Menyimpan data log privat/lokal (misal: aktivitas login user).

RDF Store (SPARQL): Menghubungkan ke basis pengetahuan eksternal (MITRE ATT&CK via SEPSES).

Optimized for Gemini: Dikonfigurasi menggunakan model Google Gemini 1.5 Pro untuk analisis yang hemat biaya dan performa tinggi.

Safety Guardrails: Memastikan sistem hanya merespons pertanyaan yang relevan dengan domain cybersecurity.

🛠️ Persiapan Sistem
1. Prasyarat
Sudah menginstal uv.

Memiliki akun Neo4j Aura (Free Tier).

Memiliki Google AI API Key (Gemini).

2. Instalasi (Clean Install)
Untuk menghindari error serialization (cannot pickle), pastikan kamu menginstal library dengan versi yang stabil:

Bash
# Clone repository
git clone <url-repository-kamu>
cd multi-agents-cykg-rag

# Buat lingkungan virtual
uv venv
source .venv/Scripts/activate  # Untuk Windows: .venv\Scripts\activate

# Install library dengan versi yang dikunci (Krusial)
uv pip install pydantic==1.10.12 langchain==0.1.20 langgraph==0.0.53 langchain-google-genai==1.0.3 langchain-neo4j==0.1.1 langchain-huggingface==0.0.3 python-dotenv
3. Konfigurasi Environment (.env)
Buat file .env di folder utama dan isi sebagai berikut:

Cuplikan kode
GOOGLE_API_KEY=AIzaSy...
NEO4J_AURA=neo4j+ssc://<instance-id>.databases.neo4j.io
NEO4J_AURA_USERNAME=neo4j
NEO4J_AURA_PASSWORD=<password-aura-kamu>
NEO4J_AURA_DATABASE=neo4j

# Konfigurasi LangChain (Opsional)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_PROJECT=AgCyRAG-Research
📊 Ingesti Data ke Neo4j
Sebelum menjalankan aplikasi, kamu harus mengisi Neo4j Aura dengan data log:

Buka Neo4j LLM Graph Builder.

Hubungkan ke instance Aura kamu.

Unggah file log (misal: daryl_auth.txt) dan klik Generate Graph.

Pastikan data muncul di tab Explore pada konsol Aura.

🖥️ Menjalankan Aplikasi
Gunakan perintah berikut untuk mengajukan pertanyaan analisis:

Bash
uv run -m src.run -- "Identifikasi aktivitas mencurigakan oleh user Daryl dan mitigasinya"
❓ Troubleshooting (Penting!)
Error AuthError: Unauthorized: Pastikan NEO4J_AURA_USERNAME adalah neo4j (bukan ID instance).

Error DatabaseNotFound: Jangan menentukan nama database secara manual di kode; biarkan driver memilih secara otomatis atau gunakan nama neo4j.

Error cannot pickle: Pastikan kamu sudah melakukan downgrade Pydantic ke versi 1.10.12.

Masalah Koneksi: Jika menggunakan jaringan kampus/kantor dan gagal konek, gunakan Hotspot Seluler dan gunakan protokol neo4j+ssc:// di file .env.

📂 Struktur Proyek
Plaintext
├── src/
│   ├── agents/          # Logika spesifik setiap agen (Vector, Cypher, SPARQL)
│   ├── config/          # Pengaturan LLM (Gemini) dan Database
│   ├── graph/           # Definisi State dan Workflow LangGraph
│   └── run.py           # Entry point aplikasi
├── browser_mcp.json     # Konfigurasi server RDF Explorer
└── requirements.txt     # Daftar library dengan versi stabil
