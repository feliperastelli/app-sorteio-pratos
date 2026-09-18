import streamlit as st
import gspread
from datetime import datetime
import random
import re
from PIL import Image

# 1. Configuração da página (com novo ícone)
st.set_page_config(page_title="Inscrição - Benditas Mulheres", page_icon="🦋", layout="centered")

# 2. Estilo CSS customizado com as cores da paleta do logo (Bordô/Magenta escuro)
st.markdown("""
    <style>
    .stButton>button {
        background-color: #8E163B;
        color: white;
        border: none;
        width: 100%;
        border-radius: 8px;
        padding: 10px;
    }
    .stButton>button:hover {
        background-color: #6C112D;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Definição das novas categorias e limites
LIMITES_PRATOS = {
    "Salgados fritos": 50,
    "Pasteizinhos": 50,
    "Salgados assados": 50,
    "Pãezinhos recheados": 50
}
TOTAL_VAGAS = sum(LIMITES_PRATOS.values())

@st.cache_resource(ttl=60)
def conectar_planilha():
    cred_dict = dict(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(cred_dict)
    
    # Lembre-se de colar a URL correta da sua planilha aqui
    url_planilha = "https://docs.google.com/spreadsheets/d/13MDIaYXIvX_nUBZ8jvarpqkFxbn4WLUOBvqd-4MZRHY/edit?hl=pt-br&gid=0#gid=0"
    return gc.open_by_url(url_planilha).sheet1

def limpar_telefone(tel: str) -> str:
    """Remove caracteres não numéricos para comparação segura."""
    return re.sub(r"\D", "", str(tel))

def main():
    # 4. Cabeçalho com o Logo da Igreja (Centralizado e menor)
    col_logo1, col_logo2, col_logo3 = st.columns([1, 1, 1])
    with col_logo2:
        try:
            st.image("image_255acd.jpg", use_container_width=True)
        except Exception:
            st.warning("Logo não encontrado. Certifique-se de que o arquivo 'image_255acd.jpg' está na mesma pasta.")

    st.markdown("<h3 style='text-align: center; color: #8E163B; margin-top: -10px;'>Confirmação de Presença</h3>", unsafe_allow_html=True)
    
    try:
        sheet = conectar_planilha()
        registros = sheet.get_all_records()
    except Exception as e:
        # Aqui adicionamos o {e} para ver exatamente o que está quebrando
        st.error(f"Erro ao conectar na planilha. Detalhe técnico: {e}")
        return

    # 5. Contagem dinâmica das vagas preenchidas
    contagem = {cat: 0 for cat in LIMITES_PRATOS.keys()}
    for r in registros:
        cat_atual = str(r.get("Categoria", "")).strip().capitalize()
        if cat_atual in contagem:
            contagem[cat_atual] += 1

    vagas_ocupadas = sum(contagem.values())

    if vagas_ocupadas >= TOTAL_VAGAS:
        st.warning("Todas as 200 inscrições já foram preenchidas! Nos vemos no evento.")
        return

    # 6. Informações de Pagamento (QR Code e Copia e Cola separados)
    st.markdown("---")
    st.markdown("### 💰 Pagamento da Inscrição")
    st.write("**Valor:** R$ 20,00")
    
    col_qr1, col_qr2 = st.columns([1, 2])
    with col_qr1:
        try:
            st.image("image_255b43.png", use_container_width=True)
        except Exception:
            st.warning("QR Code não encontrado.")
            
    with col_qr2:
        st.write("Abra o aplicativo do seu banco, escolha a opção **PIX Copia e Cola** e utilize o código gerado abaixo.")
        st.write("Após o pagamento, preencha o formulário para garantir a vaga.")

    # Bloco de código em linha dedicada (ocupando a largura total para o botão não sobrepor)
    st.code("00020126630014BR.GOV.BCB.PIX0114648858450001940223Igreja Bendita Familia 520400005303986540520.005802BR5925IGREJA EVANGELICA BENDITA6006ARARAS62070503***63049A60")

    st.markdown("---")

    # 7. Formulário de Inscrição
    with st.form("form_presenca"):
        nome = st.text_input("Nome Completo")
        telefone = st.text_input("Telefone (WhatsApp)", placeholder="(00) 00000-0000")
        submit = st.form_submit_button("Confirmar Inscrição")

    if submit:
        nome_limpo = nome.strip()
        tel_digitos = limpar_telefone(telefone)

        if not nome_limpo:
            st.error("Por favor, informe seu nome completo.")
            return
        if len(tel_digitos) < 10:
            st.error("Por favor, informe um telefone válido com DDD.")
            return

        linha_existente = None
        categoria_atribuida = None

        # Verifica se já está cadastrado
        for idx, reg in enumerate(registros):
            tel_reg = limpar_telefone(reg.get("Telefone", ""))
            if tel_reg == tel_digitos:
                linha_existente = idx + 2
                categoria_atribuida = reg.get("Categoria")
                break

        # Caso: Usuário já cadastrado
        if linha_existente:
            try:
                with st.spinner("Atualizando seus dados..."):
                    sheet.update_cell(linha_existente, 2, nome_limpo)
                
                st.info(f"Olá, {nome_limpo}! Sua inscrição já consta em nosso sistema.")
                exibir_resultado(categoria_atribuida)
                return
            except Exception as e:
                st.error("Erro ao atualizar os dados. Tente novamente.")
                return

        # Caso: Novo Cadastro (Lógica de distribuição)
        categorias_disponiveis = [
            cat for cat, limite in LIMITES_PRATOS.items() if contagem[cat] < limite
        ]

        if not categorias_disponiveis:
            st.error("Desculpe, ocorreu um erro na distribuição das vagas.")
            return

        categoria_definida = random.choice(categorias_disponiveis)
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        try:
            with st.spinner("Registrando inscrição..."):
                sheet.append_row([agora, nome_limpo, telefone.strip(), categoria_definida])
            
            st.success(f"Inscrição confirmada com sucesso, {nome_limpo}!")
            exibir_resultado(categoria_definida)
            st.balloons()
            
        except Exception as e:
            st.error("Erro ao salvar sua confirmação. Tente novamente.")

def exibir_resultado(categoria: str):
    # Transforma "Salgados fritos" em "salgados fritos" para encaixar na frase
    cat = str(categoria).strip().lower()
    
    st.markdown(
        f"""
        <div style="background-color: #F8E9ED; padding: 20px; border-radius: 10px; border-left: 5px solid #8E163B; margin-top: 15px;">
            <h4 style="color: #8E163B; margin: 0;">👉 No dia do evento, por gentileza, leve: <b>{cat}</b>.</h4>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.warning("📸 **Tire um print desta tela** agora para guardar a informação do item que você deverá levar!")

if __name__ == "__main__":
    main()