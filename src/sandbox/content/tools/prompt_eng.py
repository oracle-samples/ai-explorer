"""
Copyright (c) 2024, 2025, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.

This script initializes a web interface for setting the chatbot instr using Streamlit (`st`).

Session States Set:
- prompts_config: Stores all Prompt Examples
"""
# spell-checker:ignore selectbox

import inspect
import streamlit as st
from streamlit import session_state as state

import sandbox.utils.st_common as st_common
import sandbox.utils.api_call as api_call
import common.logging_config as logging_config

logger = logging_config.logging.getLogger("sandbox.tools.prompt_eng")

# Set endpoint if server has been established
API_ENDPOINT = None
if "server" in state:
    API_ENDPOINT = f"{state.server['url']}:{state.server['port']}/v1/prompts"


#####################################################
# Functions
#####################################################
def get_prompts(force: bool=False) -> dict[str, dict]:
    """Get a dictionary of all Prompts"""
    if "prompts_config" not in state or state["prompts_config"] == {} or force:
        try:
            api_url = f"{state.server['url']}:{state.server['port']}/v1/prompts"
            state["prompts_config"] = api_call.get(url=api_url)
            logger.info("State created: state['prompts_config']")
        except api_call.ApiError as ex:
            logger.error("Unable to retrieve prompts: %s", ex)
            st.error(f"Unable to retrieve prompts: {ex}", icon="🚨")
            state["prompts_config"] = {}


def patch_prompt(category: str, name: str, prompt: str) -> None:
    """Update Prompt Instructions"""
    if "prompts_config" not in state:
        get_prompts()

    # Check if the prompt instructions are changed
    configured_prompt = next(
        item["prompt"] for item in state["prompts_config"] if item["name"] == name and item["category"] == category
    )
    if configured_prompt != prompt:
        try:
            api_url = f"{state.server['url']}:{state.server['port']}/v1/prompts/{category}/{name}"
            api_call.patch(
                url=api_url,
                payload={"json": {"prompt": prompt}},
            )
            # Success
            logger.info("Prompt instructions updated for: %s (%s)", name, category)
            st.success(f"{name} ({category}) Prompt Instructions - Updated", icon="✅")
            st_common.clear_state_key(f"selected_prompt_{category}_name")
            st_common.clear_state_key(f"prompt_{category}_prompt")
            st_common.clear_state_key("prompts_config")
            get_prompts()  # Refresh the Config
        except api_call.ApiError as ex:
            logger.info("Unable to perform prompt update for %s (%s): %s", name, category, ex)
            st.error(f"Unable to perform prompt update: {ex}", icon="🚨")
    else:
        st.info(f"{name} ({category}) Prompt Instructions - No Changes Detected.", icon="ℹ️")


#############################################################################
# MAIN
#############################################################################
def main():
    """Streamlit GUI"""
    st.header("Prompt Engineering")
    st.write("Select which prompts to use and their instructions.  Currently selected prompts are used.")
    get_prompts()  # Create/Rebuild state

    st.subheader("System Prompt")
    sys_dict = {item["name"]: item["prompt"] for item in state.prompts_config if item["category"] == "sys"}
    with st.container(border=True):
        selected_prompt_sys_name = st.selectbox(
            "Current System Prompt: ",
            options=list(sys_dict.keys()),
            index=list(sys_dict.keys()).index(state.user_settings["prompts"]["sys"]),
            key="selected_prompts_sys",
            on_change=st_common.update_user_settings("prompts"),
        )
        prompt_sys_prompt = st.text_area(
            "System Instructions:",
            value=sys_dict[selected_prompt_sys_name],
            height=150,
            key="prompt_sys_prompt",
        )
        if st.button("Save Instructions", key="save_sys_prompt"):
            patch_prompt("sys", selected_prompt_sys_name, prompt_sys_prompt)

    st.subheader("Context Prompt")
    ctx_dict = {item["name"]: item["prompt"] for item in state.prompts_config if item["category"] == "ctx"}
    with st.container(border=True):
        selected_prompt_ctx_name = st.selectbox(
            "Current Context Prompt: ",
            options=list(ctx_dict.keys()),
            index=list(ctx_dict.keys()).index(state.user_settings["prompts"]["ctx"]),
            key="selected_prompts_ctx",
            on_change=st_common.update_user_settings("prompts"),
        )
        prompt_ctx_prompt = st.text_area(
            "Context Instructions:",
            value=ctx_dict[selected_prompt_ctx_name],
            height=150,
            key="prompt_ctx_prompt",
        )
        if st.button("Save Instructions", key="save_ctx_prompt"):
            patch_prompt("ctx", selected_prompt_ctx_name, prompt_ctx_prompt)


if __name__ == "__main__" or "page.py" in inspect.stack()[1].filename:
    main()
