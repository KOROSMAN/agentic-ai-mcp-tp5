"""SAV multi-agents : un orchestrateur LangGraph route chaque demande vers un agent spécialisé."""
import csv
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
REGISTRE = ROOT / "data" / "sav" / "garanties.csv"

llm = ChatOllama(model="qwen3:4b", temperature=0, reasoning=True)


# ---------- 1. L'état partagé ----------
class EtatSAV(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    image_ref: str | None            # référence de la photo jointe, ex. "img_px200_01"
    categorie: str | None            # "documentation" ou "garantie"
    agent: str | None                # agent sélectionné par l'orchestrateur
    reponse_finale: str | None


# ---------- 2. L'orchestrateur ----------
class Classification(BaseModel):
    categorie: Literal["documentation", "garantie"] = Field(
        description="documentation = dépannage / question sur l'appareil ; garantie = vérification de garantie")
    justification: str = Field(description="Une phrase expliquant le choix")


classifieur = llm.with_structured_output(Classification)


def orchestrateur(etat: EtatSAV) -> dict:
    if etat.get("reponse_finale"):                   # un agent a rendu la main avec une réponse
        print("🎯 [orchestrateur] réponse finale disponible -> fin")
        return {}
    question = etat["messages"][-1].content
    c = classifieur.invoke([
        SystemMessage("Tu es l'orchestrateur d'un SAV d'appareils électroniques. Classe la demande du client "
                      "dans UNE seule catégorie : documentation (panne, voyant, pictogramme, utilisation) "
                      "ou garantie (savoir si l'appareil est encore couvert, numéro de série)."),
        HumanMessage(question),
    ])
    agent = "agent_documentaire" if c.categorie == "documentation" else "agent_garantie"
    print(f"🎯 [orchestrateur] catégorie = {c.categorie} -> {agent} ({c.justification})")
    return {"categorie": c.categorie, "agent": agent}


def router(etat: EtatSAV) -> str:
    return END if etat.get("reponse_finale") else etat["agent"]


# ---------- 3. L'agent documentaire (outil DISTANT via MCP) ----------
client_mcp = MultiServerMCPClient({
    "sav": {"url": "http://127.0.0.1:24001/mcp", "transport": "streamable_http"},
})


async def agent_documentaire(etat: EtatSAV) -> dict:
    outils = await client_mcp.get_tools()            # récupère rag_multimodal depuis le serveur MCP
    agent = create_agent(
        model=llm, tools=outils,
        system_prompt=("Tu es l'agent documentaire du SAV. Appelle l'outil rag_multimodal avec la question "
                       "du client, et avec image_ref si une photo est jointe. Transmets ensuite sa réponse "
                       "sourcée au client, en français, sans inventer."),
    )
    question = etat["messages"][-1].content
    if etat.get("image_ref"):
        question += f"\n(Photo jointe : image_ref = {etat['image_ref']})"
    resultat = await agent.ainvoke({"messages": [HumanMessage(question)]})
    for m in resultat["messages"]:
        for appel in getattr(m, "tool_calls", None) or []:
            print(f"📚 [agent_documentaire] appel MCP {appel['name']}({appel['args']})")
    reponse = resultat["messages"][-1].content
    return {"messages": [AIMessage(reponse, name="agent_documentaire")], "reponse_finale": reponse}


# ---------- 4. L'agent garantie (outil LOCAL, registre en lecture seule) ----------
@tool
def consulter_garantie(numero_serie: str) -> dict:
    """Consulte le registre des garanties (lecture seule) pour un numéro de série, ex. PX200-0042."""
    with open(REGISTRE, newline="", encoding="utf-8") as f:     # ouverture en lecture uniquement
        for ligne in csv.DictReader(f):
            if ligne["numero_serie"].upper() == numero_serie.strip().upper():
                achat = date.fromisoformat(ligne["date_achat"])
                mois = int(ligne["duree_garantie_mois"])
                annee, mois_fin = divmod(achat.month - 1 + mois, 12)
                fin = achat.replace(year=achat.year + annee, month=mois_fin + 1)
                return {"numero_serie": ligne["numero_serie"], "modele": ligne["modele"],
                        "date_achat": ligne["date_achat"], "fin_garantie": fin.isoformat(),
                        "sous_garantie": date.today() <= fin, "date_du_jour": date.today().isoformat()}
    return {"erreur": f"Numéro de série {numero_serie} introuvable dans le registre."}


agent_garantie_react = create_agent(
    model=llm, tools=[consulter_garantie],
    system_prompt=("Tu es l'agent garantie du SAV. Utilise consulter_garantie avec le numéro de série fourni, "
                   "puis indique clairement si l'appareil est sous garantie et jusqu'à quelle date. "
                   "Si le numéro manque ou est introuvable, dis-le. Réponds en français."),
)


def agent_garantie(etat: EtatSAV) -> dict:
    resultat = agent_garantie_react.invoke({"messages": [HumanMessage(etat["messages"][-1].content)]})
    for m in resultat["messages"]:
        for appel in getattr(m, "tool_calls", None) or []:
            print(f"🛡️ [agent_garantie] appel local {appel['name']}({appel['args']})")
    reponse = resultat["messages"][-1].content
    return {"messages": [AIMessage(reponse, name="agent_garantie")], "reponse_finale": reponse}


# ---------- 5. Le graphe ----------
workflow = StateGraph(EtatSAV)
workflow.add_node("orchestrateur", orchestrateur)
workflow.add_node("agent_documentaire", agent_documentaire)
workflow.add_node("agent_garantie", agent_garantie)
workflow.add_edge(START, "orchestrateur")
workflow.add_conditional_edges("orchestrateur", router,
                               {"agent_documentaire": "agent_documentaire",
                                "agent_garantie": "agent_garantie", END: END})
workflow.add_edge("agent_documentaire", "orchestrateur")    # l'agent rend la main à l'orchestrateur
workflow.add_edge("agent_garantie", "orchestrateur")
graph = workflow.compile()


async def traiter_demande(question: str, image_ref: str | None = None) -> dict:
    return await graph.ainvoke({"messages": [HumanMessage(question)], "image_ref": image_ref,
                                "categorie": None, "agent": None, "reponse_finale": None})