AgCyRAG: Agentic Graph RAG for Cybersecurity Analysis
AgCyRAG adalah sistem Multi-Agent berbasis graf yang dirancang untuk otomatisasi analisis kerentanan dan mitigasi risiko keamanan siber. Sistem ini menggabungkan kekuatan Label Property Graph (LPG) untuk data log lokal dan Resource Description Framework (RDF) untuk basis pengetahuan global (MITRE ATT&CK) melalui Model Context Protocol (MCP).

🚀 Fitur Utama
Hybrid Search: Menggabungkan Vector Search (Semantik), kueri Cypher (Struktural), dan kueri SPARQL (Global Knowledge).

Multi-Agent Orchestration: Menggunakan LangGraph untuk mengatur alur kerja agen (Guardrails, Router, Analisis Log, dan Synthesizer).

Advanced Knowledge Integration: Menghubungkan log lokal dengan database MITRE ATT&CK menggunakan protokol MCP.

Robust Architecture: Solusi isolasi subprocess untuk menangani konflik memori asinkron (pickling error) pada sistem operasi Windows.

Privacy-Aware Reasoning: Mekanisme anomimisasi otomatis untuk menjaga privasi entitas lokal saat melakukan kueri ke basis pengetahuan eksternal.

🛠️ Instalasi
1. Prasyarat
Python 3.12+

UV Package Manager (direkomendasikan)

Akun Neo4j AuraDB (Free Tier)

Google Gemini API Key

2. Setup Lingkungan
Bash
# Clone repositori
```
git clone https://github.com/username/no-log-multi-agents-cykg-rag.git
cd no-log-multi-agents-cykg-rag
```
# Instal dependensi menggunakan uv
uv sync
3. Konfigurasi .env
Buat file .env di direktori root:
```
Cuplikan kode
GOOGLE_API_KEY=your_gemini_api_key
NEO4J_URI=neo4j+ssc://your_instance_id.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```
4. Konfigurasi browser_mcp.json
Sesuaikan jalur executable python ke environment lokal Anda:
```
JSON
{
  "mcpServers": {
    "mitre-attack": {
      "command": "C:/path/to/your/project/.venv/Scripts/python.exe",
      "args": ["-m", "mcp_server_module"]
    }
  }
}
```
🛡️ Solusi Teknis (Technical Highlights)Penanganan Error cannot pickle '_asyncio.Future'

Sistem ini menggunakan teknik isolasi subprocess pada _mcp_runner.py untuk menjalankan Agen MCP. Hal ini dilakukan karena LangGraph melakukan checkpointing (deepcopy) pada state agen, yang secara bawaan gagal jika agen memegang koneksi gRPC asinkron aktif. Dengan menjalankan MCP di subprocess terpisah dan berkomunikasi via stdin/stdout, stabilitas sistem terjaga 100%.

Mekanisme Generalisasi Pertanyaan
Untuk menjaga privasi dan akurasi kueri ke basis pengetahuan MITRE ATT&CK, sistem secara otomatis mengubah pertanyaan spesifik lokal:

Input: "Identifikasi aktivitas mencurigakan oleh user Daryl."

Anonymized Question: "What are the common attack patterns associated with repeated authentication failures and what are the recommended mitigations?"

🚀 Cara Menjalankan
Gunakan perintah berikut untuk memulai analisis:

```Bash
uv run -m src.run -- "Identifikasi aktivitas mencurigakan oleh user Daryl"
```
```
📂 Struktur Proyek
Plaintext
no-log-multi-agents-cykg-rag/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── _mcp_runner.py        # ISOLASI: Runner subprocess untuk MCP Agent
│   │   ├── mcp_rdf_agent.py     # Wrapper untuk memanggil runner MCP
│   │   ├── cypher_agent.py      # Agen kueri struktural Neo4j
│   │   ├── log_analysis_agent.py # Analis & Generator Pertanyaan (Generalisasi)
│   │   ├── reflection_agents.py  # Agen evaluasi kualitas jawaban
│   │   └── vector_agent.py      # Agen pencarian semantik (Vector Index)
│   ├── chains/
│   │   ├── __init__.py
│   │   ├── guardrails.py        # Validasi keamanan input pengguna
│   │   ├── review.py           # Reviewer hasil analisis
│   │   └── synthesizer.py      # Finalisasi jawaban (Analisis Kritis)
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Konfigurasi LLM (Gemini) & Database
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py            # Definisi State LangGraph
│   │   └── workflow.py         # Orkestrasi alur kerja (Graph Definition)
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logging_config.py
│   └── run.py                   # Entry point aplikasi
├── browser_mcp.json             # Konfigurasi bridge Model Context Protocol
├── pyproject.toml               # Dependensi proyek (UV Manager)
└── .env                         # Environment variables (API Keys & DB)
```
