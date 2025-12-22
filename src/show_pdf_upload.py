import streamlit as st

from src.core_utils import pdf_bytes_to_text

def process_uploaded_pdf(uploaded_file):
    st.write("Processing the uploaded PDF...")
    file_bytes = uploaded_file.read()
    if not file_bytes:
        st.warning("The uploaded PDF is empty.")
        return
    extracted_text = pdf_bytes_to_text(file_bytes)
    st.text_area("Extracted PDF text", extracted_text, height=360)

def show_upload_pdf_ui(user):
    st.write(f"Welcome to the PDF Upload tab, {user.name}!")
    st.write("This is where you can upload and discuss PDFs.")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file:
        st.write(f"Uploaded file: {uploaded_file.name}")
        # Here you can add more functionality to process and display the PDF content
        process_uploaded_pdf(uploaded_file)
