import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random

# Configuração da página
st.set_page_config(page_title="Sorteio de Pratos", page_icon="🍽️")

MAX_SALGADOS = 90
MAX_DOCES = 90

@st.cache_resource(ttl=600)
def conectar_planilha():
    cred_dict = st.secrets["gcp_service_account"]
    scopes = [
        "https://spreadsheets.google.com/feeds", 
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scopes)
    client = gspread.authorize(creds)
    
    # Lembre-se de colocar o nome exato da sua planilha aqui
    return client.open("Nome_Da_Sua_Planilha").worksheet("Respostas")

def main():
    st.title("Confirmação de Presença 🍽️")
    st.write("Preencha seus dados para confirmar presença e saber o que levar!")
    
    try:
        sheet = conectar_planilha()
        registros = sheet.get_all_records()
    except Exception as e:
        st.error(f"Erro ao conectar na planilha. Detalhes: {e}")
        return

    # Conta quantas vagas já foram ocupadas
    qtd_salgados = sum(1 for r in registros if r.get("Categoria") == "Salgado")
    qtd_doces = sum(1 for r in registros if r.get("Categoria") == "Doce")

    # Verifica se o limite de 180 já estourou
    if qtd_salgados >= MAX_SALGADOS and qtd_doces >= MAX_DOCES:
        st.warning("Todas as 180 vagas já foram preenchidas! Nos vemos no evento.")
        return

    # Formulário atualizado
    with st.form("form_sorteio"):
        nome = st.text_input("Nome Completo")
        telefone = st.text_input("Telefone (WhatsApp)")
        submit = st.form_submit_button("Confirmar e Sortear")

    if submit:
        # Validação de campos em branco
        if not nome.strip() or not telefone.strip():
            st.error("Por favor, preencha o seu nome e o seu telefone.")
            return
            
        # Validação para evitar cadastros duplicados (usando o telefone como chave)
        telefones_cadastrados = [str(r.get("Telefone", "")).strip() for r in registros]
        if telefone.strip() in telefones_cadastrados:
            st.warning(f"O telefone {telefone} já está registrado na nossa lista!")
            return

        # Lógica de balanceamento dinâmico
        categorias_disponiveis = []
        if qtd_salgados < MAX_SALGADOS:
            categorias_disponiveis.append("Salgado")
        if qtd_doces < MAX_DOCES:
            categorias_disponiveis.append("Doce")

        # Sorteia a categoria
        categoria_sorteada = random.choice(categorias_disponiveis)
        
        # Define a frase exata que aparecerá na tela
        frase_final = f"Levar um prato {categoria_sorteada.lower()}"

        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Escrita na planilha com os novos campos
        try:
            with st.spinner("Registrando..."):
                sheet.append_row([agora, nome.strip(), telefone.strip(), categoria_sorteada])
            
            # Mostra a mensagem de sucesso e a frase exata solicitada
            st.success(f"Presença confirmada, {nome}!")
            st.info(f"👉 **{frase_final}**")
            st.balloons()
            
        except Exception as e:
            st.error("Erro ao salvar os dados. Tente novamente.")

if __name__ == "__main__":
    main()
