"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

Session States Set:
- user_client: Stores the SandboxClient
"""

# spell-checker:ignore streamlit, oraclevs
import asyncio
import inspect
import json

import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.client as client
from sandbox.content.config.models import get_models
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.content.chatbot")


#############################################################################
# Functions
#############################################################################
def show_rag_refs(context):
    """When RAG Content Found, show the references"""
    st.markdown("**References:**")
    ref_src = set()
    ref_cols = st.columns([3, 3, 3])
    # Create a button in each column
    for i, ref_col in enumerate(ref_cols):
        with ref_col.popover(f"Reference: {i + 1}"):
            chunk = context[0][i]
            logger.debug("Chunk Content: %s", chunk)           
            st.subheader("Reference Text", divider="red")
            st.markdown(chunk["page_content"])
            try:
                ref_src.add(chunk["metadata"]["filename"])
                st.subheader("Metadata", divider="red")
                st.markdown(f"File:  {chunk['metadata']['source']}")
                st.markdown(f"Chunk: {chunk['metadata']['page']}")
            except KeyError:
                logger.error("Chunk Metadata NOT FOUND!!")

    for link in ref_src:
        st.markdown("- " + link)
    st.markdown(f"**Notes:** Vector Search Query - {context[1]}")


#############################################################################
# MAIN
#############################################################################
async def main() -> None:
    """Streamlit GUI"""

    #########################################################################
    # Sidebar Settings
    #########################################################################
    # Get a list of available language models, if none, then stop
    get_models(model_type="ll", force=True, only_enabled=True)
    available_ll_models = list(state.ll_model_enabled.keys())
    if not available_ll_models:
        st.error("No language models are configured and/or enabled. Disabling Sandbox.", icon="🛑")
        st.stop()
    # the sidebars will set this to False if not everything is configured.
    state.enable_sandbox = True
    st_common.history_sidebar()
    st_common.ll_sidebar()
    st_common.rag_sidebar()
    # Stop when sidebar configurations not set
    if not state.enable_sandbox:
        st.stop()

    #########################################################################
    # Chatty-Bot Centre
    #########################################################################
    # Establish the SandboxClient
    if "user_client" not in state:
        state.user_client = client.SandboxClient(
            server=state.server,
            settings=state["user_settings"],
            timeout=1200,
        )
    user_client: client.SandboxClient = state.user_client

    history = await user_client.get_history()
    st.chat_message("ai").write("Hello, how can I help you?")
    rag_refs = []
    for message in history:
        if not message["content"]:
            continue
        if message["role"] == "tool" and message["name"] == "oraclevs_tool":
            rag_refs = json.loads(message["content"])
        if message["role"] in ("ai", "assistant"):
            with st.chat_message("ai"):
                st.markdown(message["content"])
                if rag_refs:
                    show_rag_refs(rag_refs)
                    rag_refs = []
        elif message["role"] in ("human", "user"):
            st.chat_message("human").write(message["content"])

    sys_prompt = state["user_settings"]["prompts"]["sys"]
    if human_request := st.chat_input(f"Ask your question here... (current prompt: {sys_prompt})"):
        st.chat_message("human").write(human_request)
        try:
            message_placeholder = st.chat_message("ai").empty()
            full_answer = ""
            async for chunk in user_client.stream(message=human_request):
                full_answer += chunk
                message_placeholder.markdown(full_answer)
            # Stream until we hit the end then refresh to replace with history
            st.rerun()
        except Exception:
            logger.error("Exception:", exc_info=1)
            st.chat_message("ai").write(
                """
                I'm sorry, something's gone wrong.  Please try again.
                If the problem persists, please raise an issue.
                """
            )
            if st.button("Retry", key="reload_chatbot"):
                st_common.clear_state_key("user_client")
                st.rerun()


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    try:
        asyncio.run(main())
    except ValueError as ex:
        logger.exception("Bug detected: %s", ex)
        st.error("It looks like you found a bug; please open an issue", icon="🛑")
        st.stop()
    except IndexError as ex:
        logger.exception("Unable to contact the server: %s", ex)
        st.error("Unable to contact the server, is it running?", icon="🚨")
        if st.button("Retry", key="reload_chatbot"):
            st_common.clear_state_key("user_client")
            st.rerun()
