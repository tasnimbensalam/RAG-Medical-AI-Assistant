import streamlit as st
from utils.api import ask_question

# Même début de phrase que le refus du prompt (server/modules/llm.py) : pas de sources sous un refus.
REFUSAL_PREFIX = "désolé, je n'ai pas trouvé"


def show_sources(sources):
    if sources:
        st.markdown("📄 **Sources :**")
        for src in sources:
            st.markdown(f"- `{src}`")


def is_refusal(answer: str) -> bool:
    return answer.strip().lower().replace("’", "'").startswith(REFUSAL_PREFIX)


def render_chat():
    st.subheader("💬 Chat with your assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # render existing chat history (sources included)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            show_sources(msg.get("sources"))

    # input and response
    user_input = st.chat_input("Type your question....")
    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        response = ask_question(user_input)
        if response.status_code == 200:
            data = response.json()
            answer = data["response"]
            sources = [] if is_refusal(answer) else data.get("sources", [])
            with st.chat_message("assistant"):
                st.markdown(answer)
                show_sources(sources)
            st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
        else:
            st.error(f"Error: {response.text}")