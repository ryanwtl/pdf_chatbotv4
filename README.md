# 📄 PDF Chatbot with Summarization and QA Capabilities

This is a powerful Streamlit-based application that allows users to upload one or more PDF documents, ask questions about their content, or request summaries. The app leverages vector search using FAISS, LLM-based reasoning via Groq, and evaluates the quality of summaries using semantic similarity (SpaCy) and ROUGE-1 metrics.

---

## 🚀 Features

- Upload multiple PDF files
- Interactive Q&A using Groq's LLMs
- Text summarization with section-level context retention
- ROUGE and SpaCy-based summary evaluation
- Semantic similarity scoring
- Vector store generation using FAISS and Google Generative AI embeddings
- Clean, responsive Streamlit UI

---

## 📁 Repository Structure

```bash
.
├── app.py                # Main application logic and Streamlit UI
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/pdf-chatbot-app.git
cd pdf-chatbot-app
```

### 2. Create a Virtual Environment (Optional but Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download SpaCy Models

The application uses SpaCy for semantic similarity. Install the required language models:

```bash
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md
```

### 5. Set Up Environment Variables

Create a `.env` file in the root directory and add the following keys:

```
GOOGLE_API_KEY=your_google_genai_key
GROQ_API_KEY=your_groq_api_key
```

---

## ▶️ Running the App

Once all dependencies are installed and your `.env` is configured:

```bash
streamlit run app.py
```

This will launch the app in your default web browser.

---

## 🧠 How It Works

1. **Upload PDFs:** Upload one or multiple PDFs through the sidebar.
2. **Vectorization:** Documents are split into chunks and embedded using Google Generative AI embeddings.
3. **Query or Summarize:**
   - **Ask Questions:** Select a Groq model and enter your query.
   - **Summarize:** Include words like "summary" or "summarize" in your prompt to trigger the summarization pipeline.
4. **Evaluation:** Summaries are scored using:
   - **Semantic Similarity (SpaCy)**
   - **ROUGE-1 Score**

---

## 📌 Notes

- Ensure your `.env` file contains valid API keys.
- Some Groq models used in this app: `llama3-70b-8192`, `llama-3.1-70b-versatile`, and `llama-3.3-70b-versatile`.
- Vector store is stored in-memory and is rebuilt on each upload.
- If you're using this in production, consider persisting the vector store locally or in a database.

---

## 📚 Requirements Overview

**Key Libraries Used:**

- `streamlit`: Interactive UI
- `langchain`: Vector store, embeddings, prompt templating
- `FAISS`: Vector similarity search
- `groq`: LLM API interaction
- `spacy`: NLP preprocessing and similarity scoring
- `rouge-score`: Summarization evaluation
- `python-dotenv`: Secure API key management

---

## 🛠️ Troubleshooting

- **App crashes on file upload:** Make sure your PDF is not corrupted.
- **API errors:** Double-check your API keys and rate limits.
- **Slow response:** Summarization and vectorization may take time for large documents.

---

## 📬 Feedback and Contributions

Feel free to open issues, suggest features, or submit PRs!
