# src/config/settings.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# --- Environment Variables ---
google_api_key = os.environ.get("GOOGLE_API_KEY")

# Neo4j
neo4j_uri = os.environ.get("NEO4J_AURA")
neo4j_username = os.environ.get("NEO4J_AURA_USERNAME")
neo4j_password = os.environ.get("NEO4J_AURA_PASSWORD")
database=os.getenv("NEO4J_AURA_DATABASE")

# Langchain
os.environ["LANGCHAIN_TRACING_V2"] = os.environ.get("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_PROJECT"] = os.environ.get("LANGCHAIN_PROJECT")
os.environ["LANGCHAIN_API_KEY"] = os.environ.get("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_ENDPOINT"] = os.environ.get("LANGCHAIN_ENDPOINT", "")

# --- LLM init ---
# 2. Gunakan objek Enum untuk safety_settings agar lolos validasi Pydantic
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=google_api_key,
    temperature=0,
    transport="rest",  # <--- KUNCI UTAMA: Wajib ada untuk mencegah error '_asyncio.Future'
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
)

# Koneksi ke eksternal (MITRE ATT&CK)
graph = Neo4jGraph(
    url=neo4j_uri,
    username=neo4j_username,
    password=neo4j_password,   
    database=database
)

# --- Global Configs & Schema ---
DEFAULT_MAX_ITERATIONS = 3
NEO4J_SCHEMA_RAW = graph.schema
NEO4J_SCHEMA_ESCAPED_FOR_PROMPT = NEO4J_SCHEMA_RAW.replace("{", "{{").replace("}", "}}")

VECTOR_INDEX_NAME = "vector"
KEYWORD_INDEX_NAME = "keyword"

# --- Embeddings Model ---
model_name = "sentence-transformers/all-MiniLM-L6-v2"
embeddings = HuggingFaceEmbeddings(model_name=model_name)

# --- Vector Index Init ---
vector_index = Neo4jVector.from_existing_index(
    embedding=embeddings,
    url=neo4j_uri,
    username=neo4j_username,
    password=neo4j_password,
    database=database,
    index_name=VECTOR_INDEX_NAME,
    keyword_index_name=KEYWORD_INDEX_NAME,
    search_type="hybrid"
)