import streamlit as st  
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.evaluation import load_evaluator
from langchain.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
import tempfile
import uuid
import re
import base64
from dotenv import load_dotenv
import os
import time
import spacy
from groq import Groq


# Load the spaCy model (make sure to download it first using python -m spacy download en_core_web_sm)
nlp = spacy.load("en_core_web_sm")

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys from environment variables
google_api_key = os.getenv("GOOGLE_API_KEY")
groqcloud_api_key = os.getenv("GROQ_API_KEY")
client = Groq()

# Ensure API key is set
if not groqcloud_api_key:
    st.error("GroqCloud API key not found. Please set GROQCLOUD_API_KEY in your .env file.")

def display_pdf(uploaded_file):

    """
    Display a PDF file that has been uploaded to Streamlit.

    The PDF will be displayed in an iframe, with the width and height set to 700x1000 pixels.

    Parameters
    ----------
    uploaded_file : UploadedFile
        The uploaded PDF file to display.

    Returns
    -------
    None
    """
    # Read file as bytes:
    bytes_data = uploaded_file.getvalue()
    
    # Convert to Base64
    base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
    
    # Embed PDF in HTML
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    
    # Display file
    st.markdown(pdf_display, unsafe_allow_html=True)

def split_document(documents, chunk_size, chunk_overlap):    
    """
    Function to split generic text into smaller chunks.
    chunk_size: The desired maximum size of each chunk (default: 400)
    chunk_overlap: The number of characters to overlap between consecutive chunks (default: 20).

    Returns:
        list: A list of smaller text chunks created from the generic text
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                          chunk_overlap=chunk_overlap,
                                          length_function=len,
                                          separators=["\n\n", "\n", " "])
    
    return text_splitter.split_documents(documents)


def preprocess_question(question):
    # Step 1: Remove leading/trailing whitespace
    question = question.strip()
    
    # Step 4: Process the question using spaCy
    doc = nlp(question)
    
    # Step 5: Lowercase, remove punctuation, and lemmatize
    preprocessed_tokens = []
    for token in doc:
        if not token.is_punct and not token.is_stop:  # Exclude punctuation and stopwords
            preprocessed_tokens.append(token.lemma_.lower())  # Lemmatize and lowercase
    
    # Final preprocessed text
    preprocessed_question = ' '.join(preprocessed_tokens)
    preprocessed_question = preprocessed_question.capitalize()
    
    return preprocessed_question

def get_embedding_function():
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def create_vectorstore(chunks, embedding_function, file_name):

    """
    Create a vector store from a list of text chunks.

    :param chunks: A list of generic text chunks
    :param embedding_function: A function that takes a string and returns a vector
    :param file_name: The name of the file to associate with the vector store
    :param vector_store_path: The directory to store the vector store

    :return: A Chroma vector store object
    """

    # Create a list of unique ids for each document based on the content
    ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.page_content)) for doc in chunks]
    
    # Ensure that only unique docs with unique ids are kept
    unique_ids = set()
    unique_chunks = []
    
    unique_chunks = [] 
    for chunk, id in zip(chunks, ids):     
        if id not in unique_ids:       
            unique_ids.add(id)
            unique_chunks.append(chunk)        

    print("Creating Vector Store...")
    # Create a new Chroma database from the documents
    vectorstore = FAISS.from_documents(documents=unique_chunks, 
                                        embedding=embedding_function, 
                                        ids=list(unique_ids))
    # vectorstore.save_local(file_name)
    
    return vectorstore


def create_vectorstore_from_texts(documents, file_name):
    
    # Step 2 split the documents  
    """
    Create a vector store from a list of texts.

    :param documents: A list of generic text documents
    :param api_key: The OpenAI API key used to create the vector store
    :param file_name: The name of the file to associate with the vector store

    :return: A Chroma vector store object
    """
    docs = split_document(documents, chunk_size=1000, chunk_overlap=50)
    
    # Step 3 define embedding function
    embedding_function = get_embedding_function()

    # Step 4 create a vector store  
    vectorstore = create_vectorstore(docs, embedding_function, file_name)
    
    return vectorstore

def evaluate_chunks(chunks,question):
    """
    Evaluate the similarity between the chunks and the question.

    Parameters:
        chunks (list): A list of text chunks to evaluate
        question (str): The question to evaluate the chunks against

    Returns:
        list: A list of tuples containing the chunk and its similarity score to the question
    """
    # Preprocess the question
    preprocessed_question = preprocess_question(question)

    embeddings = get_embedding_function()

    evaluator = load_evaluator(evaluator="embedding_distance", 
                            embeddings=embeddings)
    
    # Evaluate the similarity between the chunks and the question
    similarity_scores = []
    for chunk in chunks:
        # Preprocess the chunk
        preprocessed_chunk = preprocess_question(chunk.page_content)
        
        # Calculate the similarity score between the chunk and the question
        similarity_score = evaluator.evaluate(preprocessed_question, preprocessed_chunk)
        
        # Store the similarity score and the chunk
        similarity_scores.append((chunk, similarity_score))

    for chunk in similarity_scores:
        print(similarity_scores)
    
    return similarity_scores


def get_pdf_text(uploaded_file): 
    """
    Load a PDF document from an uploaded file and return it as a list of documents

    Parameters:
        uploaded_file (file-like object): The uploaded PDF file to load

    Returns:
        list: A list of documents created from the uploaded PDF file
    """
    try:
        # Read file content
        input_file = uploaded_file.read()

        # Create a temporary file (PyPDFLoader requires a file path to read the PDF,
        # it can't work directly with file-like objects or byte streams that we get from Streamlit's uploaded_file)
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(input_file)
        temp_file.close()
        loader = PyPDFLoader(temp_file.name)
        documents = loader.load() 

        return documents
    
    finally:
        # Ensure the temporary file is deleted when we're done with it
        os.unlink(temp_file.name)

# Prompt template
PROMPT_TEMPLATE = """
If you don't know the answer, say that you
don't know. DON'T MAKE UP ANYTHING.

{context}

---

Answer the question based on the above context: {question}
"""

def generate_summary_messages(content):
    """Create the messages payload that will be sent to the Groq LLM API."""
    return [
        {
            "role": "system",
            "content": """You are an assistant for summarizing text. 
                        Summarize the section given but maintain the key points.
                        The summary first explaining the section then in the end give a summary overall.
                        """
        },
        {
            "role": "user",
            "content": content
        }
    ]

def generate_query_messages(content):
    """Create the messages payload that will be sent to the Groq LLM API."""
    return [
        {
            "role": "system",
            "content": """You are an assistant for question-answering tasks.
                        Use the following pieces of retrieved context to answer
                        the question. 
                        """
        },
        {
            "role": "user",
            "content": content
        }
    ]

def summary_function(vectorstore, model_name, question="summarize the whole content"):
    """
    Summarize the provided text by interacting with the Groq LLM model.

    Args:
        text (str): The input text that needs to be summarized.

    Returns:
        dict: A dictionary containing the original text and its corresponding summary.
    """

    retriever=vectorstore.as_retriever(search_type="similarity")

    topic = preprocess_question(question)

    # retriever=FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    relevant_chunks = retriever.invoke(topic)

    # relevant_chunks = retriever.similarity_search(topic)

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=relevant_chunks, question=topic)

    print(relevant_chunks)
    print(topic)

    # Create the messages payload for the Groq LLM model
    messages = generate_summary_messages(prompt)

    # Send the request to the Groq model and get the response
    response = client.chat.completions.create(
        model=model_name,  # Ensure this model name is correct
        messages=messages,
        temperature=1,
        max_tokens=500,
        top_p=1,
        stream=False,
    )


    # Extract and store the summary from the response
    text_summary = response.choices[0].message.content

    return text_summary

def query_document(vectorstore, query, model_name):

    """
    Query a vector store with a question and return a structured response.

    :param vectorstore: A Chroma vector store object
    :param query: The question to ask the vector store
    :param api_key: The OpenAI API key to use when calling the OpenAI Embeddings API

    :return: A pandas DataFrame with three rows: 'answer', 'source', and 'reasoning'
    """
    retriever=vectorstore.as_retriever(search_type="similarity")
    topic = preprocess_question(query)

    relevant_chunks = retriever.invoke(topic)

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=relevant_chunks, question=topic)

    messages = generate_query_messages(prompt)

    print(relevant_chunks)
    print(topic)

    # Send the request to the Groq model and get the response
    response = client.chat.completions.create(
        model=model_name,  # Ensure this model name is correct
        messages=messages,
        temperature=1,
        max_tokens=500,
        top_p=1,
        stream=False,
    )

    result = response.choices[0].message.content

    return result

def load_streamlit_page():

    """
    Load the streamlit page with two columns. The left column contains a text input box for the user to input their OpenAI API key, and a file uploader for the user to upload a PDF document. The right column contains a header and text that greet the user and explain the purpose of the tool.

    Returns:
        col1: The left column Streamlit object.
        col2: The right column Streamlit object.
        uploaded_file: The uploaded PDF file.
    """
    st.set_page_config(layout="wide", page_title="PDF Chatbot")

    # Design page layout with 2 columns: File uploader on the left, and other interactions on the right.
    col1, col2 = st.columns([0.5, 0.5], gap="large")

    with col1:
        st.header("WELCOME")

        uploaded_file = st.file_uploader("Please upload your PDF document:", type= "pdf", accept_multiple_files=True)

    return col1, col2, uploaded_file

# Initialize session state variables
if "uploaded" not in st.session_state:
    st.session_state.uploaded = False

# Make a streamlit page
col1, col2, uploaded_file = load_streamlit_page()

# Process multiple files
if uploaded_file:  # Check if at least one file is uploaded
    documents = []
    for file in uploaded_file:
        with col2:
            # Display each uploaded PDF file
            display_pdf(file)
        
        # Load the text from each uploaded file
        file_documents = get_pdf_text(file)
        documents.extend(file_documents)  # Combine documents from all files
    
    # Create a single vector store for all the combined documents
    st.session_state.vector_store = create_vectorstore_from_texts(
        documents=documents, 
        file_name="CombinedDocuments"
    )
    print("Vector store created successfully.")
    st.session_state.uploaded = True

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

# Generate answer
with col1:
    if not st.session_state.uploaded:
        st.info("Please upload PDF document first.")
    else:
        model_name = st.selectbox("Select Model:", ["Llama3","Llama3.1","Llama3.3"])
        model_mapping = {
            "Llama3": "llama3-70b-8192",
            "Llama3.1": "llama-3.1-70b-versatile", 
            "Llama3.3": "llama-3.3-70b-versatile" 
        }

        user_question = st.text_input("Question:", placeholder="Ask about your PDF", key='input')
        if st.button("Send"):
            start_time = time.time()
            with st.spinner("Generating answer"):
                if any(keyword in user_question.lower() for keyword in ["summarize", "summary"]):
                    # Call the summary function
                    answer = summary_function(vectorstore=st.session_state.vector_store,
                                              model_name=model_mapping[model_name],
                                              question=user_question)
                    print('Summarize complete')
                else:
                    # Proceed with the QA flow
                    answer = query_document(
                        vectorstore=st.session_state.vector_store, 
                        query=user_question,
                        model_name=model_mapping[model_name]
                    )
                
                # Record the query and response in the chat history for the selected model
                if model_name not in st.session_state.chat_history:
                    st.session_state.chat_history[model_name] = []
                st.session_state.chat_history[model_name].append({
                    "question": user_question,
                    "answer": answer
                })

                placeholder = st.empty()
                placeholder = st.write(answer)
            elapsed_time = time.time() - start_time
            st.write(f"Response Time: {elapsed_time:.2f} seconds")

        # Display chat history for the selected model
        st.subheader("Chat History")
        show_history = st.checkbox("Show Chat History", value=True)

        if show_history and model_name in st.session_state.chat_history:
            for idx, chat in enumerate(st.session_state.chat_history[model_name], start=1):
                # User question on the right
                st.markdown(
                    f"""
                    <div style="text-align: right; margin: 10px;">
                        <div style="display: inline-block; background-color: #d1f0d1; color: black; padding: 10px; border-radius: 10px;">
                            {chat['question']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # Model answer on the left
                st.markdown(
                    f"""
                    <div style="text-align: left; margin: 10px;">
                        <div style="display: inline-block; background-color: #d8eaff; color: black; padding: 10px; border-radius: 10px;">
                            {chat['answer']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )