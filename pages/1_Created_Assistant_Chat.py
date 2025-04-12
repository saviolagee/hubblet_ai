import streamlit as st
from utils import get_assistant_response, client, model
from components import create_header
import time

def create_new_custom_chat():
    """Create a new chat thread for the custom assistant"""
    # Generate new chat ID
    chat_id = f"chat_{len(st.session_state.custom_chat_history) + 1}"
    
    # Save current chat if it exists
    if st.session_state.custom_assistant_messages:
        st.session_state.custom_chat_history[st.session_state.current_custom_chat_id] = {
            'messages': st.session_state.custom_assistant_messages.copy(),
            'thread_id': st.session_state.custom_assistant_thread.id,
            'timestamp': time.strftime("%d/%m/%Y %H:%M")
        }
    
    # Create new chat
    st.session_state.custom_assistant_messages = []
    st.session_state.custom_assistant_thread = client.beta.threads.create()
    st.session_state.current_custom_chat_id = chat_id

def main():
    st.set_page_config(layout="wide")
    
    # Create header navigation
    create_header()
    
    # Initialize chat history if not exists
    if 'custom_chat_history' not in st.session_state:
        st.session_state.custom_chat_history = {}
    if 'current_custom_chat_id' not in st.session_state:
        st.session_state.current_custom_chat_id = "chat_1"
    
    # Get assistant name from session state or use default
    assistant_name = st.session_state.get('assistant_name', 'Assistente Criado')
    st.title(f"Chat com {assistant_name}")
    
    # Check if a custom assistant exists
    if 'custom_assistant' not in st.session_state:
        st.warning("Primeiro crie um assistente personalizado no modo Customização!")
        st.info("Volte à página principal e clique em 'Customizar' para criar seu assistente.")
        return
    
    # Initialize messages and thread if not exists
    if 'custom_assistant_messages' not in st.session_state:
        st.session_state.custom_assistant_messages = []
    if 'custom_assistant_thread' not in st.session_state:
        st.session_state.custom_assistant_thread = client.beta.threads.create()
    
    # Sidebar with chat history
    with st.sidebar:
        st.title("Menu")
        
        # New Chat button at the top of sidebar
        if st.button("🔄 Novo Chat", use_container_width=True):
            create_new_custom_chat()
            st.rerun()
        
        st.markdown("---")
        st.subheader("Histórico de Chats")
        
        # Display saved chats
        for chat_id, chat_data in st.session_state.custom_chat_history.items():
            first_message = "Novo chat"
            if chat_data['messages']:
                first_message = chat_data['messages'][0]['content'][:30] + "..."
            
            if st.button(f"{chat_data['timestamp']} - {first_message}", key=f"custom_{chat_id}"):
                st.session_state.custom_assistant_messages = chat_data['messages'].copy()
                st.session_state.custom_assistant_thread = client.beta.threads.retrieve(chat_data['thread_id'])
                st.session_state.current_custom_chat_id = chat_id
                st.rerun()
    
    # Display assistant info
    with st.expander("ℹ️ Informações do Assistente"):
        assistant_info = client.beta.assistants.retrieve(st.session_state.custom_assistant.id)
        st.write("**Nome:**", assistant_info.name)
        st.write("**Instruções do Assistente:**")
        st.markdown(assistant_info.instructions.replace("Instruções baseadas na conversa:\n\n", ""))
    
    # Chat interface
    chat_container = st.container()
    input_container = st.container()
    
    # Display chat history
    with chat_container:
        for message in st.session_state.custom_assistant_messages:
            cols = st.columns([6, 6])
            if message["role"] == "assistant":
                with cols[0]:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
            else:
                with cols[1]:
                    with st.chat_message("user"):
                        st.write(message["content"])
    
    with input_container:
        st.markdown("---")
        cols = st.columns([0.9, 0.1])
        prompt = cols[0].chat_input("Digite sua mensagem...")
        
        if prompt:
            st.session_state.custom_assistant_messages.append({"role": "user", "content": prompt})
            
            # Use the custom assistant for responses
            response = get_assistant_response(
                st.session_state.custom_assistant_thread.id,
                st.session_state.custom_assistant.id,
                prompt
            )
            st.session_state.custom_assistant_messages.append({"role": "assistant", "content": response})
            st.rerun()

if __name__ == "__main__":
    main() 