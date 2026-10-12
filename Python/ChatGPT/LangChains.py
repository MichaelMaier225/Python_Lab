import os
import sys
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_openai import OpenAI

load_dotenv()

PDF_NAMES = ["Cats.pdf", "Dogs.pdf"]  # List of predefined PDFs


def main():
    question = input("What would you like to know about? ").strip()
    if not question:
        print("You must enter a question.")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key not found. Set it in the .env file.")
        return

    combined_text = extract_data(PDF_NAMES)
    if not combined_text:
        print("No valid text could be extracted from the provided PDFs.")
        return

    docs = split_text(combined_text)
    if not docs:
        print("No text chunks could be created from the extracted text.")
        return

    docstorage = vectorize_and_store(docs, api_key)
    response = answer_question(question, api_key, docstorage)

    print(response["result"] if response and "result" in response else "No result found.")


def extract_data(pdf_names):
    combined_text = ""
    for pdf_name in pdf_names:
        try:
            loader = PyPDFLoader(pdf_name)
            data = loader.load()
            combined_text += "".join(doc.page_content for doc in data if hasattr(doc, "page_content"))
        except Exception as e:
            print(f"Error loading {pdf_name}: {e}")
    return combined_text


def split_text(text):
    splitter = CharacterTextSplitter(separator=".", chunk_size=1200, chunk_overlap=200)
    return splitter.split_text(text)


def vectorize_and_store(docs, api_key):
    embedding_function = OpenAIEmbeddings(openai_api_key=api_key)
    return FAISS.from_texts(docs, embedding_function)


def answer_question(question, api_key, docstorage):
    llm = OpenAI(model_name="gpt-3.5-turbo-instruct", openai_api_key=api_key)
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=docstorage.as_retriever())
    return qa.invoke({"query": question})


if __name__ == "__main__":
    main()
