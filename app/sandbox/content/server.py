"""
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
"""
# spell-checker:ignore streamlit, oaim

import os
import asyncio
import inspect
import time

import streamlit as st
from streamlit import session_state as state

import oaim_server
import sandbox.utils.api_call as api_call
import sandbox.utils.client as client
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.content.server")


#####################################################
# Functions
#####################################################
def initialize() -> None:
    """initialize Streamlit Session State"""
    if "server" not in state:
        logger.info("Initializing state.server")
        state.server = {"url": os.getenv("API_SERVER_URL", "http://localhost")}
        state.server["port"] = int(os.getenv("API_SERVER_PORT", "8000"))
        state.server["pid"] = oaim_server.start_server(state.server["port"])
        state.server["key"] = os.getenv("API_SERVER_KEY")


def server_restart() -> None:
    """Restart the server process when button pressed"""
    os.environ["API_SERVER_KEY"] = state.user_server_key
    state.server["port"] = state.user_server_port
    state.server["key"] = os.getenv("API_SERVER_KEY")

    oaim_server.stop_server(state.server["pid"])
    state.server["pid"] = oaim_server.start_server(state.server["port"])
    state.pop("sever_client", None)


def copy_user_settings() -> None:
    api_url = f"{state.server['url']}:{state.server['port']}/v1/settings"
    try:
        api_call.patch(
            url=api_url,
            params={"client": "server"},
            payload={"json": state.user_settings},
        )
        st.success("Server Settings - Updated", icon="✅")
    except api_call.ApiError as ex:
        st.success("Server Settings - Update Failed", icon="❌")
        logger.error("Server Settings Update failed: %s", ex)


#####################################################
# MAIN
#####################################################
async def main() -> None:
    """Streamlit GUI"""
    initialize()
    st.header("API Server")
    st.write("Access the Sandbox with your own client.")
    left, right = st.columns([0.2, 0.8])
    left.number_input(
        "API Server Port:",
        value=state.server["port"],
        key="user_server_port",
        min_value=1,
        max_value=65535,
    )
    right.text_input(
        "API Server Key:",
        value=state.server["key"],
        key="user_server_key",
        type="password",
    )
    st.button("Restart Server", type="primary", on_click=server_restart)

    st.header("Server Configuration", divider="red")
    st.json(state.server_settings, expanded=False)
    st.button("Copy User Settings", type="primary", on_click=copy_user_settings)

    st.header("Server Activity", divider="red")
    if "server_client" not in state:
        state.server_client = client.SandboxClient(
            server=state.server,
            settings=state["server_settings"],
            timeout=10,
        )
    server_client: client.SandboxClient = state.server_client

    auto_refresh = st.toggle("Auto Refresh", value=False, key="selected_auto_refresh")
    st.button("Refresh", disabled=auto_refresh)
    with st.container():
        history = await server_client.get_history()
        for message in history:
            if message["role"] in ("ai", "assistant"):
                st.chat_message("ai").json(message, expanded=False)
            elif message["role"] in ("human", "user"):
                st.chat_message("human").json(message, expanded=False)
        if auto_refresh:
            time.sleep(10)  # Refresh every 10 seconds
            st.rerun()
    # for message in history:
    #     st.write(message)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    asyncio.run(main())
