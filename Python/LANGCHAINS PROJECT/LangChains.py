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

PDF_NAMES = ["Cats.pdf", "Dogs.pdf", "Horses.pdf"]  # List of PDFs


def main():
    question = input("What would you like to know about? ").strip()
    if not question:
        print("You must enter a question.")  # Error message for empty input
        return

    api_key = os.getenv("OPENAI_API_KEY")  # API Key in .env
    if not api_key:
        print("Error: OpenAI API key not found. Set it in the .env file.")
        return

    combined_text = extract_data(PDF_NAMES)  # Combines all text in PDFs into one string
    if not combined_text:
        print("No valid text could be extracted from the provided PDFs.")
        return

    docs = split_text(combined_text)  # Split the big text into smaller parts so it's easier to process
    if not docs:
        print("No text chunks could be created from the extracted text.")
        return

    docstorage = vectorize_and_store(docs, api_key)  # Stores the data
    response = answer_question(question, api_key, docstorage)  # Answers the user's question based on the PDFs

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
    return splitter.split_text(text)  # Creates overlap in the chunks to give more context


def vectorize_and_store(docs, api_key):
    embedding_function = OpenAIEmbeddings(openai_api_key=api_key)  # Turns text into something a computer can understand
    return FAISS.from_texts(docs, embedding_function)  # Creates and returns a FAISS vector store


def answer_question(question, api_key, docstorage):
    llm = OpenAI(model_name="gpt-3.5-turbo-instruct", openai_api_key=api_key)  # Connect to GPT
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=docstorage.as_retriever())
    return qa.invoke({"query": question})  # Ask the question and get the answer


if __name__ == "__main__":
    main()
