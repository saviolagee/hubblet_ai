import streamlit as st
import time
import openai
from dotenv import load_dotenv
import os
from utils import get_assistant_response, client, model
from components import create_header

# Load environment variables
load_dotenv()

# OpenAI client setup
client = openai.OpenAI()
model = "gpt-3.5-turbo"

def create_assistant():
    """Create or get assistant"""
    if 'assistant' not in st.session_state:
        st.session_state.assistant = client.beta.assistants.create(
            name="Assistente de Vendas",
            instructions="Você é um assistente de vendas experiente. Use o arquivo fornecido para entender o produto e responder às perguntas do usuário.",
            tools=[{"type": "file_search"}] if st.session_state.get('uploaded_files', []) else [],
            model=model
        )
    return st.session_state.assistant

def add_file_to_assistant(file_data, assistant_id):
    """Upload and attach file to assistant"""
    try:
        # Upload file
        file_response = client.files.create(
            file=file_data,
            purpose="assistants"
        )
        
        file_id = file_response.id
        
        # Create Vector Store and associate file
        vector_store = client.beta.vector_stores.create(name="Instruction Vector Store")
        vector_store_id = vector_store.id
        
        # Add file to Vector Store
        client.beta.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_id)
        
        # Associate Vector Store with assistant
        client.beta.assistants.update(
            assistant_id, 
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )
        
        # After file is uploaded, send a message to analyze it
        message = client.beta.threads.messages.create(
            thread_id=st.session_state.customizer_thread.id,
            role="user",
            content="Por favor, analise o documento que acabei de enviar e me ajude a criar um assistente especializado neste assunto."
        )
        
        return file_id
        
    except Exception as e:
        raise Exception(f"Erro ao processar arquivo: {str(e)}")

def create_new_thread():
    """Create a new thread and store it in session state"""
    st.session_state.thread = client.beta.threads.create()
    st.session_state.messages = []

def create_instruction_assistant():
    """Create or get the instruction helper assistant"""
    if 'instruction_assistant' not in st.session_state:
        st.session_state.instruction_assistant = client.beta.assistants.create(
            name="Assistente de Configuração",
            instructions="""Você é um especialista em criar instruções para assistentes AI. 
            
            Se um arquivo for fornecido, primeiro leia e analise seu conteúdo. Use essas informações para 
            ajudar o usuário a criar um assistente especializado no assunto do documento.
            
            Ajude o usuário a definir as instruções para seu novo assistente, fazendo perguntas relevantes sobre:
            - O propósito do assistente (considerando o conteúdo do documento, se fornecido)
            - O tom de voz desejado
            - Conhecimentos específicos necessários
            - Limitações e restrições
            - Formato das respostas
            
            Mantenha um tom profissional e faça uma pergunta por vez.
            
            Quando o usuário terminar de responder suas perguntas, compile todas as informações em um conjunto 
            claro de instruções e as apresente precedidas por "INSTRUÇÕES FINAIS:".
            
            As instruções finais devem ser claras, diretas e completas, incluindo referências ao conteúdo 
            do documento quando relevante.""",
            model=model,
            tools=[{"type": "file_search"}]  # Enable file search capability
        )
    return st.session_state.instruction_assistant

def create_custom_assistant_from_thread(thread_id, assistant_name):
    """Create a new assistant using the conversation thread as instructions"""
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    
    # Extract the final instructions from the conversation
    instructions = ""
    for msg in reversed(messages.data):
        if msg.role == "assistant" and "INSTRUÇÕES FINAIS:" in msg.content[0].text.value:
            instructions = msg.content[0].text.value.split("INSTRUÇÕES FINAIS:")[1].strip()
            break
    
    if not instructions:
        # If no final instructions found, compile all assistant messages
        conversation = []
        for msg in messages.data:
            if msg.role == "assistant":
                conversation.append(msg.content[0].text.value)
        instructions = "\n\n".join(conversation)
    
    # Create the new assistant with clear instructions
    custom_assistant = client.beta.assistants.create(
        name=assistant_name,
        instructions=f"""Suas instruções específicas são:

{instructions}

Mantenha-se fiel a estas instruções em todas as suas respostas.""",
        model=model
    )
    
    # Initialize session state for custom assistant
    st.session_state.custom_assistant = custom_assistant
    st.session_state.custom_assistant_messages = []
    st.session_state.custom_assistant_thread = client.beta.threads.create()
    
    return custom_assistant

def main():
    st.set_page_config(layout="wide")
    
    # Create header navigation
    create_header()
    
    # Initialize session state variables
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'thread' not in st.session_state:
        st.session_state.thread = client.beta.threads.create()
    if 'current_mode' not in st.session_state:
        st.session_state.current_mode = "Modo Customização"
    if 'custom_instructions' not in st.session_state:
        st.session_state.custom_instructions = "MUDAR DEPOIS"
    if 'customizer_messages' not in st.session_state:
        st.session_state.customizer_messages = []
    if 'customizer_thread' not in st.session_state:
        st.session_state.customizer_thread = client.beta.threads.create()

    # Main chat area with dynamic title
    st.title(f"{st.session_state.current_mode}")
    
    # Always show customization mode
    st.caption("Converse com o assistente especializado para criar as instruções do seu novo assistente")
    
    # Add a button to finish customization
    if st.session_state.customizer_messages:  # Only show if there are messages
        # First check if we're already in naming mode
        if 'naming_mode' not in st.session_state:
            st.session_state.naming_mode = False
        if 'temp_name' not in st.session_state:
            st.session_state.temp_name = ""
        
        if not st.session_state.naming_mode:
            if st.button("✨ Criar Assistente com estas Instruções"):
                st.session_state.naming_mode = True
                st.rerun()
        
        # Show name input if in naming mode
        if st.session_state.naming_mode:
            # Use a temporary variable for the name
            temp_name = st.text_input(
                "Nome do Assistente", 
                value=st.session_state.temp_name,
                placeholder="Digite um nome para seu assistente..."
            )
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("Confirmar"):
                    if temp_name.strip():  # Check if name is not empty
                        # Create new assistant using the conversation
                        custom_assistant = create_custom_assistant_from_thread(
                            st.session_state.customizer_thread.id,
                            temp_name
                        )
                        # Save to session state for use in the other page
                        st.session_state.custom_assistant = custom_assistant
                        st.session_state.assistant_name = temp_name
                        st.session_state.naming_mode = False
                        st.session_state.temp_name = ""  # Clear temporary name
                        st.success(f"Assistente '{temp_name}' criado com sucesso! Acesse-o através do menu superior.")
                        st.rerun()
                    else:
                        st.error("Por favor, digite um nome para o assistente.")
            
            with col2:
                if st.button("Cancelar"):
                    st.session_state.naming_mode = False
                    st.session_state.temp_name = ""  # Clear temporary name
                    st.rerun()
            
            # Store the current name in session state
            st.session_state.temp_name = temp_name
    
    # Create main container for customizer chat
    chat_container = st.container()
    input_container = st.container()
    
    # Display messages
    with chat_container:
        for message in st.session_state.customizer_messages:
            cols = st.columns([6, 6])
            if message["role"] == "assistant":
                with cols[0]:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
            else:
                with cols[1]:
                    with st.chat_message("user"):
                        st.write(message["content"])
    
    # Input area for customizer
    with input_container:
        st.markdown("---")
        cols = st.columns([0.9, 0.1])
        prompt = cols[0].chat_input("Descreva o assistente que você quer criar...")
        
        # File upload handling
        if 'show_uploader' not in st.session_state:
            st.session_state.show_uploader = False
            
        # Toggle file uploader visibility
        if cols[1].button("📎"):
            st.session_state.show_uploader = not st.session_state.show_uploader
            st.rerun()
            
        # Show file uploader if button was clicked
        if st.session_state.show_uploader:
            uploaded_file = st.file_uploader(
                "Selecione um arquivo",
                type=['pdf', 'txt'],
                key="customizer_uploader"
            )
            if uploaded_file:
                try:
                    # Get or create instruction assistant
                    instruction_assistant = create_instruction_assistant()
                    
                    # Add file to assistant
                    file_id = add_file_to_assistant(uploaded_file, instruction_assistant.id)
                    
                    # Add system message about the file
                    file_message = f"Arquivo '{uploaded_file.name}' foi carregado para referência."
                    st.session_state.customizer_messages.append({"role": "system", "content": file_message})
                    
                    st.success(f"Arquivo carregado: {uploaded_file.name}")
                    st.session_state.show_uploader = False  # Hide uploader after success
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao carregar arquivo: {str(e)}")
        
        if prompt:
            # Add user message
            st.session_state.customizer_messages.append({"role": "user", "content": prompt})
            
            # Get response from instruction assistant
            instruction_assistant = create_instruction_assistant()
            response = get_assistant_response(
                st.session_state.customizer_thread.id,
                instruction_assistant.id,
                prompt
            )
            st.session_state.customizer_messages.append({"role": "assistant", "content": response})
            
            # If the response contains formatted instructions, save them
            if "INSTRUÇÕES FINAIS:" in response:
                st.session_state.custom_instructions = response.split("INSTRUÇÕES FINAIS:")[1].strip()
                st.success("Instruções salvas com sucesso!")
            
            st.rerun()

if __name__ == "__main__":
    main() 