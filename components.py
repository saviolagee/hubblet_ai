import streamlit as st

def create_header():
    """Create consistent header navigation across pages"""
    with st.container():
        cols = st.columns([2, 2, 8])  # Adjust column ratios as needed
        
        with cols[0]:
            st.page_link("app.py", label="Página Inicial", icon="🏠")
            
        with cols[1]:
            # Get the custom assistant name or use default
            custom_assistant_name = st.session_state.get('assistant_name', 'Assistente Criado')
            st.page_link(
                "pages/1_Created_Assistant_Chat.py",
                label=f"Chat com {custom_assistant_name}",
                icon="💬"
            )
    
    st.markdown("---")  # Separator after header 