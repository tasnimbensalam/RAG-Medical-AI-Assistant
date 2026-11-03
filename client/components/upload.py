import streamlit as st
from utils.api import upload_pdfs_api


def render_uploader():
    st.sidebar.header("Upload documents (.PDFs)")
    uploaded_files=st.sidebar.file_uploader("Upload multiple PDFs",type="pdf",accept_multiple_files=True)
    if st.sidebar.button("Upload DB") and uploaded_files:
        with st.sidebar, st.spinner("Indexing..."):
            response=upload_pdfs_api(uploaded_files)
        if response.status_code in (200,400):
            data=response.json()
            for name,chunks in data.get("processed",{}).items():
                st.sidebar.success(f"{name} : {chunks} chunks indexés")
            for name,reason in data.get("errors",{}).items():
                st.sidebar.error(f"{name} : {reason}")
        else:
            st.sidebar.error(f"Error:{response.text}")
