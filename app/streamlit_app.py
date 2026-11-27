"""Interface web Streamlit pour le chatbot Agentic RAG (LangGraph)."""
import sys
import uuid
from pathlib import Path

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # pour trouver le package app
from app.rag_agent import creer_graphe

st.set_page_config(page_title="Chatbot Agentic RAG", page_icon="🤖")
st.title("🤖 Chatbot Agentic RAG")
st.caption("LangGraph · Ollama (qwen3:4b) · Chroma — posez vos questions sur les documents indexés")


@st.cache_resource          # le graphe n'est créé qu'une seule fois, pas à chaque interaction
def charger_graphe():
    return creer_graphe(checkpointer=InMemorySaver())


graphe = charger_graphe()

# Un identifiant de conversation par session de navigateur
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": st.session_state.thread_id}}

with st.sidebar:
    st.subheader("Conversation")
    st.write(f"Thread : `{st.session_state.thread_id[:8]}`")
    if st.button("🗑️ Nouvelle conversation"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# Réafficher l'historique stocké dans la mémoire du graphe
etat = graphe.get_state(config)
for message in etat.values.get("messages", []):
    if isinstance(message, HumanMessage):
        st.chat_message("user").write(message.content)
    elif isinstance(message, AIMessage) and message.content:
        st.chat_message("assistant").write(message.content)

question = st.chat_input("Votre question…")
if question:
    st.chat_message("user").write(question)
    with st.chat_message("assistant"):
        with st.spinner("L'agent réfléchit…"):
            resultat = graphe.invoke({"messages": [HumanMessage(question)]}, config=config)

        # Messages produits pendant CE tour (après la dernière question)
        nouveaux = []
        for message in reversed(resultat["messages"]):
            if isinstance(message, HumanMessage):
                break
            nouveaux.insert(0, message)

        appels = [a for m in nouveaux if isinstance(m, AIMessage) for a in m.tool_calls]
        sources = [m.content for m in nouveaux if isinstance(m, ToolMessage)]
        if appels:
            with st.expander(f"🔧 {len(appels)} appel(s) d'outil et sources"):
                for appel in appels:
                    st.write(f"**{appel['name']}** — `{appel['args']}`")
                for contenu in sources:
                    st.text(contenu[:1500])

        st.write(resultat["messages"][-1].content)