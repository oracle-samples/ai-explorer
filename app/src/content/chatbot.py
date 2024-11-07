"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, langchain, llms

import inspect

# Streamlit
import streamlit as st
from streamlit import session_state as state

# Utilities
import modules.st_common as st_common
import modules.logging_config as logging_config
import modules.chatbot as chatbot

# History
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

logger = logging_config.logging.getLogger("chatbot")


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    # Initialize RAG
    st_common.initialize_rag()
    # Setup History
    chat_history = StreamlitChatMessageHistory(key="sandbox_chat_history")

    #########################################################################
    # Sidebar Settings
    #########################################################################
    enabled_llms = sum(model_info["enabled"] for model_info in state.ll_model_config.values())
    if enabled_llms > 0:
        with st.chat_message("ai"):
            # Do not put this in the history as messages must alternate human/ai
            st.write("Hello, how can I help you?")
        enable_history = st.sidebar.checkbox(
            "Enable History and Context?",
            value=True,
            key="user_chat_history",
        )
        if st.sidebar.button("Clear History", disabled=not enable_history):
            chat_history.clear()
        st.sidebar.divider()
        ll_model = st_common.lm_sidebar()
    else:
        st.error("No chat models are configured and/or enabled.", icon="🚨")
        st.stop()

    # RAG
    st_common.rag_sidebar()

    # Save
    st_common.save_settings_sidebar()
    #########################################################################
    # Initialize the Client
    #########################################################################
    if "initialized" not in state:
        if not state.rag_params["enable"] or all(
            state.rag_params[key] for key in ["model", "chunk_size", "chunk_overlap", "distance_metric"]
        ):
            try:
                state.chat_manager = st_common.initialize_chatbot(ll_model)
                state.initialized = True
                st_common.update_rag()
                logger.debug("Force rerun to save state")
                st.rerun()
            except Exception as ex:
                logger.exception(ex, exc_info=False)
                st.error(f"Failed to initialize the chat client: {ex}")
                st_common.clear_initialized()
                if st.button("Retry", key="retry_initialize"):
                    st.rerun()
                st.stop()

    #########################################################################
    # Chatty-Bot Centre
    #########################################################################
    for msg in chat_history.messages:
        if msg.type == "AIMessageChunk":
            st.chat_message("ai").write(msg.content)
        else:
            st.chat_message(msg.type).write(msg.content)

    if "chat_manager" in state:
        if prompt := st.chat_input(f"Ask your question here... (current prompt: {state.lm_instr_prompt})"):
            st.chat_message("human").write(prompt)
            try:
                response = chatbot.generate_response(
                    chat_mgr=state.chat_manager,
                    input=prompt,
                    chat_history=chat_history,
                    enable_history=enable_history,
                    rag_params=state.rag_params,
                    chat_instr=state.lm_instr,
                    context_instr=state.context_instr,
                    stream=True,
                )
                if state.rag_params["enable"]:
                    message_placeholder = st.chat_message("ai").empty()
                    full_answer = ""
                    full_context = None

                    for chunk in response:
                        full_answer += chunk.get("answer", "")
                        if "context" in chunk:
                            full_context = chunk["context"]
                        message_placeholder.markdown(full_answer)
                    if full_context:
                        st_common.show_rag_refs(full_context)
                else:
                    st.chat_message("ai").write_stream(response)
            except Exception as ex:
                st.chat_message("ai").write(f"I'm sorry, something's gone wrong: {ex}")
                st.chat_message("ai").write("Please try refreshing your browser.")
                raise
    else:
        st.error("Not all required RAG options are set, please review or disable RAG.")


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
