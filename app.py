import streamlit as st
from PyPDF2 import PdfReader
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import os
import pandas as pd
from pptx import Presentation
import io

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# Supported file extensions
SUPPORTED_EXTENSIONS = ['pdf', 'docx', 'txt', 'csv', 'xlsx', 'xls', 'pptx', 'ppt']


def combine_text(text_list):
    return "\n".join(text_list)


def get_pdf_text(pdf_file):
    text = ""
    pdf_reader = PdfReader(pdf_file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def get_word_text(docx_file):
    document = Document(docx_file)
    text = "\n".join([paragraph.text for paragraph in document.paragraphs])
    return text


def read_text_file(txt_file):
    text = txt_file.getvalue().decode('utf-8')
    return text


def get_csv_text(csv_file):
    """Extract text content from CSV files"""
    try:
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Convert DataFrame to readable text format
        text_content = []
        
        # Add column headers
        headers = "Column Headers: " + ", ".join(df.columns.tolist())
        text_content.append(headers)
        text_content.append("\n" + "="*50 + "\n")
        
        # Add data summary
        text_content.append(f"Total Rows: {len(df)}")
        text_content.append(f"Total Columns: {len(df.columns)}")
        text_content.append("\n" + "-"*30 + "\n")
        
        # Add sample data (first few rows)
        text_content.append("Sample Data:")
        for idx, row in df.head(10).iterrows():  # Show first 10 rows
            row_text = f"Row {idx + 1}: " + " | ".join([f"{col}: {str(val)}" for col, val in row.items()])
            text_content.append(row_text)
        
        # Add data types info
        text_content.append("\n" + "-"*30 + "\n")
        text_content.append("Data Types:")
        for col, dtype in df.dtypes.items():
            text_content.append(f"{col}: {dtype}")
        
        # Add statistical summary for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            text_content.append("\n" + "-"*30 + "\n")
            text_content.append("Numeric Column Statistics:")
            for col in numeric_cols:
                stats = df[col].describe()
                text_content.append(f"{col} - Mean: {stats['mean']:.2f}, Min: {stats['min']}, Max: {stats['max']}")
        
        return "\n".join(text_content)
        
    except Exception as e:
        return f"Error reading CSV file: {str(e)}"


def get_excel_text(excel_file):
    """Extract text content from Excel files"""
    try:
        # Read all sheets from Excel file
        excel_data = pd.read_excel(excel_file, sheet_name=None)
        
        text_content = []
        text_content.append(f"Excel File contains {len(excel_data)} sheet(s)")
        text_content.append("="*50)
        
        for sheet_name, df in excel_data.items():
            text_content.append(f"\nSheet: {sheet_name}")
            text_content.append("-" * 30)
            
            # Add column headers
            headers = "Columns: " + ", ".join(df.columns.tolist())
            text_content.append(headers)
            
            # Add basic info
            text_content.append(f"Rows: {len(df)}, Columns: {len(df.columns)}")
            
            # Add sample data (first 5 rows for each sheet)
            if not df.empty:
                text_content.append("\nSample Data:")
                for idx, row in df.head(5).iterrows():
                    row_text = f"Row {idx + 1}: " + " | ".join([f"{col}: {str(val)}" for col, val in row.items()])
                    text_content.append(row_text)
            
            # Add statistical summary for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                text_content.append(f"\nNumeric Columns Summary:")
                for col in numeric_cols:
                    if not df[col].empty:
                        stats = df[col].describe()
                        text_content.append(f"{col} - Mean: {stats['mean']:.2f}, Min: {stats['min']}, Max: {stats['max']}")
        
        return "\n".join(text_content)
        
    except Exception as e:
        return f"Error reading Excel file: {str(e)}"


def get_ppt_text(ppt_file):
    """Extract text content from PowerPoint files"""
    try:
        presentation = Presentation(ppt_file)
        text_content = []
        
        text_content.append(f"PowerPoint Presentation with {len(presentation.slides)} slides")
        text_content.append("="*50)
        
        for slide_num, slide in enumerate(presentation.slides, 1):
            text_content.append(f"\nSlide {slide_num}:")
            text_content.append("-" * 20)
            
            # Extract text from all shapes in the slide
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            
            if slide_text:
                text_content.extend(slide_text)
            else:
                text_content.append("(No text content found)")
        
        return "\n".join(text_content)
        
    except Exception as e:
        return f"Error reading PowerPoint file: {str(e)}"


def is_supported_file(filename):
    """Check if file extension is supported"""
    file_ext = filename.lower().split('.')[-1]
    return file_ext in SUPPORTED_EXTENSIONS


def get_file_text(file):
    """Route file to appropriate text extraction function based on extension"""
    filename = file.name.lower()
    
    if not is_supported_file(filename):
        return f"Unsupported file format. Please upload only: {', '.join(SUPPORTED_EXTENSIONS)}"
    
    try:
        if filename.endswith('.pdf'):
            return get_pdf_text(file)
        elif filename.endswith('.docx'):
            return get_word_text(file)
        elif filename.endswith('.txt'):
            return read_text_file(file)
        elif filename.endswith('.csv'):
            return get_csv_text(file)
        elif filename.endswith(('.xlsx', '.xls')):
            return get_excel_text(file)
        elif filename.endswith(('.pptx', '.ppt')):
            return get_ppt_text(file)
        else:
            return f"Unsupported file format: {filename}"
    except Exception as e:
        return f"Error processing {filename}: {str(e)}"


def get_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    return chunks


def vector_store(text_chunks):
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_db")


def get_top_retrieval_results(retriever, question, k=5):
    """Get top k retrieval results to display on UI"""
    try:
        docs = retriever.get_relevant_documents(question)
        return docs[:k]
    except Exception as e:
        st.error(f"Error retrieving documents: {str(e)}")
        return []


def get_conversational_chain(retriever, ques, chat_history):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    # Get relevant documents
    relevant_docs = retriever.get_relevant_documents(ques)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    
    # Format chat history for context
    chat_context = ""
    if chat_history:
        chat_context = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" 
            for msg in chat_history[-6:]  # Last 6 messages for context
        ])
    
    # Create a simple prompt without agent framework
    prompt_template = """You are a helpful assistant. Answer the question as detailed as possible from the provided context.
    Make sure to provide all the details. Consider the chat history for context and continuity.
    If the answer is not in the provided context, just say "answer is not available in the context", don't provide the wrong answer.

    Chat History:
    {chat_history}

    Context from documents:
    {context}

    Question: {question}

    Answer:"""
    
    prompt = prompt_template.format(
        chat_history=chat_context,
        context=context,
        question=ques
    )
    
    # Get response directly from LLM
    response = llm.invoke(prompt)
    return response.content


def process_user_question(user_question, chat_history):
    """Process user question and return response with retrieval results"""
    try:
        new_db = FAISS.load_local("faiss_db", embeddings, allow_dangerous_deserialization=True)
        retriever = new_db.as_retriever()
        
        # Get top 5 retrieval results for this specific question
        top_results = get_top_retrieval_results(retriever, user_question, k=5)
        
        # Get response using direct RAG approach
        response = get_conversational_chain(retriever, user_question, chat_history)
        
        return response, top_results
        
    except Exception as e:
        return f"Error: Unable to process your question. Please make sure you have uploaded and processed files first. Details: {str(e)}", []


def display_retrieval_results(results, question):
    """Display retrieval results for a specific question"""
    if results:
        with st.expander(f"📄 Top 5 Retrieved Sections for: '{question[:50]}...'", expanded=False):
            for i, doc in enumerate(results, 1):
                st.write(f"**Result {i}:**")
                content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                st.write(content)
                if i < len(results):
                    st.write("---")


def get_file_icon(filename):
    """Return appropriate icon for file type"""
    filename = filename.lower()
    if filename.endswith('.pdf'):
        return "📄"
    elif filename.endswith('.docx'):
        return "📝"
    elif filename.endswith('.txt'):
        return "📄"
    elif filename.endswith('.csv'):
        return "📊"
    elif filename.endswith(('.xlsx', '.xls')):
        return "📈"
    elif filename.endswith(('.pptx', '.ppt')):
        return "📽️"
    else:
        return "📁"


def main():
    load_dotenv()
    st.set_page_config(
        page_title="ARD File Chatbot",
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'files_processed' not in st.session_state:
        st.session_state.files_processed = False
    
    if 'processed_files_info' not in st.session_state:
        st.session_state.processed_files_info = []

    st.title("🤖 ARD File Chatbot")
    st.markdown("Upload your documents and start chatting! Supports: PDF, DOCX, TXT, CSV, Excel, PowerPoint")

    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Chat interface
        if not st.session_state.files_processed:
            st.warning("⚠️ Please upload and process your files first before asking questions!")
        else:
            st.success(f"✅ Files processed successfully! You can now ask questions about your {len(st.session_state.processed_files_info)} uploaded files.")
        
        # Chat input at the top for better UX
        user_question = st.chat_input(
            "Ask a question about your documents...",
            disabled=not st.session_state.files_processed
        )
        
        # Process new question
        if user_question and st.session_state.files_processed:
            # Add user message to chat history
            st.session_state.chat_history.append({
                "role": "user", 
                "content": user_question
            })
            
            # Get response and retrieval results
            with st.spinner("Thinking..."):
                response, retrieval_results = process_user_question(user_question, st.session_state.chat_history[:-1])
            
            if "answer is not available in the context" in response.lower() or "not available in the context" in response.lower():
                retrieval_results = []

            # Add assistant response to chat history
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": response,
                "retrieval_results": retrieval_results,
                "question": user_question
            })
        
        # Display chat history with retrieval results
        st.subheader("💬 Conversation")
        
        if st.session_state.chat_history:
            # Create a scrollable container for chat
            chat_container = st.container()
            
            with chat_container:
                for i, message in enumerate(st.session_state.chat_history):
                    if message["role"] == "user":
                        with st.chat_message("user"):
                            st.write(message["content"])
                    else:
                        with st.chat_message("assistant"):
                            st.write(message["content"])
                            
                            # Show retrieval results only for this specific question-answer pair
                            if "retrieval_results" in message and message["retrieval_results"]:
                                display_retrieval_results(
                                    message["retrieval_results"], 
                                    message.get("question", "Question")
                                )
        else:
            if st.session_state.files_processed:
                st.info("👋 Start by asking a question about your uploaded documents!")
            else:
                st.info("📁 Upload and process your files to begin chatting!")
    
    with col2:
        # File management sidebar
        st.subheader("📁 File Management")
        
        # Display supported formats
        st.markdown("**Supported Formats:**")
        st.markdown("📄 PDF • 📝 DOCX • 📄 TXT • 📊 CSV • 📈 Excel • 📽️ PowerPoint")
        st.write("---")
        
        # Show processed files info
        if st.session_state.processed_files_info:
            st.write("**Processed Files:**")
            for file_info in st.session_state.processed_files_info:
                st.write(f"• {file_info}")
            st.write("---")
        
        # File upload
        files = st.file_uploader(
            "Upload your files here and click on 'Process'", 
            accept_multiple_files=True,
            type=SUPPORTED_EXTENSIONS,
            help="Supported formats: PDF, DOCX, TXT, CSV, XLSX, XLS, PPTX, PPT"
        )
        
        # Process files button
        if st.button("🔄 Process Files", type="primary", use_container_width=True):
            if not files:
                st.error("Please upload at least one file to process.")
            else:
                with st.spinner("Processing files..."):
                    try:
                        # Process different file types
                        all_texts = []
                        processed_files = []
                        error_files = []
                        
                        for file in files:
                            # Check if file is supported
                            if not is_supported_file(file.name):
                                error_files.append(f"❌ {file.name} (unsupported format)")
                                continue
                            
                            # Extract text based on file type
                            text = get_file_text(file)
                            
                            if text and not text.startswith("Error"):
                                all_texts.append(text)
                                icon = get_file_icon(file.name)
                                processed_files.append(f"{icon} {file.name}")
                            else:
                                error_files.append(f"❌ {file.name} (processing error)")
                        
                        # Show errors if any
                        if error_files:
                            st.error("Some files could not be processed:")
                            for error_file in error_files:
                                st.write(f"  {error_file}")
                        
                        # Combine all texts
                        if all_texts:
                            combined_text = combine_text(all_texts)
                            
                            if combined_text.strip():
                                # Create chunks and vector store
                                text_chunks = get_chunks(combined_text)
                                vector_store(text_chunks)
                                
                                # Update session state
                                st.session_state.files_processed = True
                                st.session_state.processed_files_info = processed_files
                                st.session_state.chat_history = []  # Reset chat for new files
                                
                                st.success(f"✅ Successfully processed {len(processed_files)} files!")
                                st.rerun()
                            else:
                                st.error("No text content found in the uploaded files.")
                        else:
                            st.error("No files were successfully processed. Please check your file formats and try again.")
                    
                    except Exception as e:
                        st.error(f"Error processing files: {str(e)}")
        
        st.write("---")
        
        # Action buttons
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                if st.session_state.chat_history:
                    st.session_state.chat_history = []
                    st.rerun()
        
        with col_b:
            if st.button("🔄 Reset All", use_container_width=True):
                if st.session_state.files_processed:
                    st.session_state.files_processed = False
                    st.session_state.processed_files_info = []
                    st.session_state.chat_history = []
                    # Clean up vector store
                    try:
                        import shutil
                        if os.path.exists("faiss_db"):
                            shutil.rmtree("faiss_db")
                    except:
                        pass
                    st.rerun()
        
        # Chat statistics
        if st.session_state.chat_history:
            st.write("---")
            st.write("**Chat Statistics:**")
            user_messages = len([msg for msg in st.session_state.chat_history if msg["role"] == "user"])
            st.write(f"• Questions asked: {user_messages}")
            st.write(f"• Total messages: {len(st.session_state.chat_history)}")


if __name__ == "__main__":
    main()