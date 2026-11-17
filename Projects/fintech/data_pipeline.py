from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


# data source

PDF_FOLDER = './bajaj_pdfs'
CHROMA_DIR = './bajajbot_chroma_db'
COLLECTION_NAME = 'bajaj_policy'
LOG_FILE ="./processed_files.json"


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 0

def load_log():
    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def save_log(log:dict):
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f)


def load_and_chunk(filepath):
    # step 1 : Load the PDF
    loader = PyPDFLoader(filepath)
    documents = loader.load()

    # split the documents into multiple chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, 
                                              chunk_overlap=CHUNK_OVERLAP)

    chunks = splitter.split_documents(documents)
    return chunks


def run_pipeline():
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(collection_name=COLLECTION_NAME, 
                         embedding_function=embedding_model,
                           persist_directory=CHROMA_DIR)
    
    pdf_files = list(Path(PDF_FOLDER).glob("*.pdf"))
    if not pdf_files:
        print("  No PDFs found. Drop PDFs into the folder and run again.")
        return
    
    for pdf_path in pdf_files:
        chunks = load_and_chunk(pdf_path)
        vectorstore.add_documents(chunks)
    


run_pipeline() 

