"""Chatbot Agentic RAG construit avec LangGraph (réutilisé par LangGraph Studio et Streamlit)."""
from pathlib import Path
from typing import Annotated, TypedDict

from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

ROOT = Path(__file__).resolve().parent.parent      # racine du projet
PDF_DIR = ROOT / "data" / "pdfs"
CHROMA_DIR = ROOT / "chroma_db"

# ---------- 1. Base vectorielle (la même qu'à l'étape 5) ----------
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma(
    collection_name="documents",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR),
)
if vectorstore._collection.count() == 0:
    pages = PyPDFDirectoryLoader(str(PDF_DIR)).load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(pages)
    vectorstore.add_documents(chunks)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})


# ---------- 2. L'outil de recherche (le BODY) ----------
@tool
def rechercher_documents(requete: str) -> str:
    """Recherche des passages dans les documents PDF indexés (notamment l'article
    "Attention Is All You Need" sur le Transformer).
    À utiliser pour toute question sur le contenu de ces documents.
    La requête doit être courte, précise et rédigée en anglais."""
    documents = retriever.invoke(requete)
    if not documents:
        return "Aucun passage trouvé."
    return "\n\n".join(
        f"[{Path(d.metadata['source']).name}, page {d.metadata.get('page', 0) + 1}] {d.page_content}"
        for d in documents
    )


outils = [rechercher_documents]

# ---------- 3. Le LLM (le MIND) ----------
llm = ChatOllama(model="qwen3:4b", temperature=0, reasoning=True)
llm_avec_outils = llm.bind_tools(outils)

PROMPT_SYSTEME = (
    "Tu es un assistant documentaire. "
    "Pour toute question sur le contenu des documents, utilise l'outil rechercher_documents "
    "avant de répondre, et ne réponds pas de mémoire. "
    "Cite tes sources sous la forme [fichier, page X]. "
    "Si l'information n'est pas dans les documents, dis-le clairement. "
    "Pour une simple salutation, réponds directement sans outil. "
    "Réponds en français."
)


# ---------- 4. Le graphe ----------
class EtatAgent(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def agent(etat: EtatAgent) -> dict:
    messages = [SystemMessage(PROMPT_SYSTEME)] + etat["messages"]
    return {"messages": [llm_avec_outils.invoke(messages)]}


def doit_continuer(etat: EtatAgent) -> str:
    return "outils" if etat["messages"][-1].tool_calls else "fin"


def creer_graphe(checkpointer=None):
    workflow = StateGraph(EtatAgent)
    workflow.add_node("agent", agent)
    workflow.add_node("outils", ToolNode(outils))
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", doit_continuer, {"outils": "outils", "fin": END})
    workflow.add_edge("outils", "agent")
    return workflow.compile(checkpointer=checkpointer)


# Graphe sans mémoire : c'est celui que charge LangGraph Studio (qui gère sa propre mémoire)
graph = creer_graphe()