"""Serveur MCP du SAV : publie l'outil rag_multimodal (agent RAG sur les manuels, texte + figures)."""
import base64
import json
from pathlib import Path

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
SAV = ROOT / "data" / "sav"

# ---------- 1. Indexation des manuels : passages + figures ----------
embeddings = OllamaEmbeddings(model="nomic-embed-text")
base = Chroma(collection_name="manuels_sav", embedding_function=embeddings,
              persist_directory=str(ROOT / "chroma_db"))

if base._collection.count() == 0:
    documents = []
    manuel = (SAV / "manuel_px200.md").read_text(encoding="utf-8")
    for bloc in manuel.split("\n## ")[1:]:                     # une section = un passage
        titre, _, texte = bloc.partition("\n")
        documents.append(Document(page_content=f"{titre}\n{texte.strip()}",
                                  metadata={"type": "passage", "source": "Manuel PX-200", "section": titre}))
    for fig in json.loads((SAV / "figures" / "figures.json").read_text(encoding="utf-8")):
        documents.append(Document(page_content=f"{fig['legende']}. {fig['description']}",
                                  metadata={"type": "figure", "source": "Manuel PX-200", "section": fig["section"],
                                            "figure": fig["legende"], "chemin": f"data/sav/figures/{fig['fichier']}"}))
    base.add_documents(documents)

retriever = base.as_retriever(search_kwargs={"k": 4})


# ---------- 2. L'agent RAG caché derrière l'outil ----------
@tool
def rechercher_manuels(requete: str) -> str:
    """Recherche des passages et des figures dans les manuels des appareils (ex. imprimante PX-200)."""
    lignes = []
    for d in retriever.invoke(requete):
        m = d.metadata
        if m["type"] == "figure":
            lignes.append(f"[{m['figure']} — {m['chemin']}] {d.page_content}")
        else:
            lignes.append(f"[{m['source']}, section {m['section']}] {d.page_content}")
    return "\n\n".join(lignes) or "Aucun résultat."


llm = ChatOllama(model="qwen3:4b", temperature=0, reasoning=True)
vlm = ChatOllama(model="qwen3-vl:4b", temperature=0)          # modèle de vision pour la photo

agent_rag = create_agent(
    model=llm,
    tools=[rechercher_manuels],
    system_prompt=(
        "Tu es l'agent RAG du service après-vente. Utilise rechercher_manuels pour trouver les passages "
        "et les figures utiles, puis réponds UNIQUEMENT à partir de ces éléments. "
        "Cite chaque source : [Manuel PX-200, section ...] pour un passage, [Figure n] pour une figure. "
        "Si les manuels ne contiennent pas la réponse, dis-le. Réponds en français."
    ),
)


def decrire_image(image_ref: str) -> str:
    """Décrit la photo jointe par le client avec le modèle de vision."""
    chemin = SAV / "images" / f"{image_ref}.png"
    if not chemin.exists():
        return f"(image {image_ref} introuvable)"
    image_b64 = base64.b64encode(chemin.read_bytes()).decode()
    message = HumanMessage(content=[
        {"type": "text", "text": "Décris précisément ce que montre cette photo d'écran d'imprimante : "
                                 "pictogramme affiché (forme, couleur) et couleur du voyant. Réponds en une ou deux phrases."},
        {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"},
    ])
    return vlm.invoke([message]).content


# ---------- 3. Le serveur MCP ----------
mcp = FastMCP("sav-rag", host="0.0.0.0", port=24001)


@mcp.tool()
def rag_multimodal(question: str, image_ref: str = "") -> str:
    """Répond à une question de dépannage à partir des manuels des appareils (passages et figures),
    avec une réponse sourcée. Si le client a joint une photo, passer sa référence dans image_ref
    (ex. "img_px200_01")."""
    contexte_image = ""
    if image_ref:
        contexte_image = f"\nDescription de la photo jointe ({image_ref}) : {decrire_image(image_ref)}"
    resultat = agent_rag.invoke({"messages": [HumanMessage(question + contexte_image)]})
    return resultat["messages"][-1].content


if __name__ == "__main__":
    mcp.run(transport="streamable-http")