import os
import time
import openai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do OpenAI
client = openai.OpenAI()
model = "gpt-4-turbo"

# Define arquivos_complementares before using it
arquivos_complementares = []  # Empty list when no files are needed

# Step 2 - Criar o assistente
assistant = client.beta.assistants.create(
    name="Assistente de Vendas",
    instructions="Você é um assistente de vendas experiente. Use o arquivo fornecido para entender o produto e responder às perguntas do usuário.",
    tools=[{"type": "file_search"}] if arquivos_complementares else [],  # Make tools conditional
    model=model
)

print(f"Assistente criado com sucesso. ID: {assistant.id}")

def adicionar_arquivo_assistente(assistant_id, file_path):
    """
    Faz o upload de um arquivo e associa ao assistente.
    Retorna o ID do arquivo processado.
    """
    file_response = openai.files.create(
        file=open(file_path, "rb"),
        purpose="assistants"
    )
    
    file_id = file_response.id
    
    # Criar um Vector Store e associar o arquivo a ele
    vector_store = openai.beta.vector_stores.create(name="Meu Vector Store")
    vector_store_id = vector_store.id
    
    # Adicionar o arquivo ao Vector Store
    openai.beta.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_id)
    
    # Associar o Vector Store ao assistente
    openai.beta.assistants.update(assistant_id, tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}})
    
    return file_id

# Make file upload section conditional
if arquivos_complementares:
    for arquivo in arquivos_complementares:
        if arquivo.strip():  # Only process non-empty file paths
            file_id = adicionar_arquivo_assistente(assistant.id, arquivo)
            print(f"Arquivo {arquivo} adicionado com ID: {file_id}")

# Step 3 - Criar a thread
thread = client.beta.threads.create()
thread_id = thread.id

print(f"Thread criada com sucesso. ID: {thread_id}")

message = client.beta.threads.messages.create(
    thread_id=thread_id,
    role="user",
    content="o que fala o documento?",
)

# Step 4 - Criar a execução do assistente referenciando o arquivo
run = client.beta.threads.runs.create(
    thread_id=thread_id,
    assistant_id=assistant.id,
    instructions="o que fala o documento?"
)


run_id = run.id
print(f"Execução iniciada. ID: {run_id}")

# Função para aguardar a conclusão da execução
def wait_for_run_completion(client, thread_id, run_id, sleep_interval=2):
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run_status.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            if messages.data:
                response = messages.data[0].content[0].text.value
                print(f"Resposta do Assistente: {response}")
                return response
            else:
                print("Nenhuma resposta encontrada.")
                return None
        elif run_status.status in ["failed", "cancelled"]:
            print(f"Execução falhou: {run_status.status}")
            return None
        else:
            print(f"Aguardando conclusão... Status atual: {run_status.status}")
            time.sleep(2)

# Esperar a conclusão da execução
wait_for_run_completion(client, thread_id, run_id)
