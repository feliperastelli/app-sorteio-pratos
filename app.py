import streamlit as st
import gspread
from datetime import datetime
import random
import re
import os

# 1. Configuração da página
st.set_page_config(page_title="Inscrição - Benditas Mulheres", page_icon="🦋", layout="centered")

# 2. Estilo CSS customizado (Otimizado para Mobile)
st.markdown("""
    <style>
    /* Botões principais */
    .stButton>button {
        background-color: #8E163B;
        color: white;
        border: none;
        width: 100%;
        border-radius: 8px;
        padding: 12px; 
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #6C112D;
        color: white;
    }
    /* Centralização de imagens no Streamlit */
    [data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    /* Espaçamento em mobile */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    </style>
""", unsafe_allow_html=True)

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
    url_planilha = "https://docs.google.com/spreadsheets/d/13MDIaYXIvX_nUBZ8jvarpqkFxbn4WLUOBvqd-4MZRHY/edit?hl=pt-br&gid=0#gid=0"
    return gc.open_by_url(url_planilha).sheet1

def limpar_telefone(tel: str) -> str:
    return re.sub(r"\D", "", str(tel))

def main():
    DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
    
    # Busca as chaves sensíveis nos Secrets
    try:
        CHAVE_PIX = st.secrets["evento"]["chave_pix"]
        WHATSAPP_CONTATO = st.secrets["evento"]["whatsapp_contato"]
    except KeyError:
        st.error("Configurações do evento (PIX ou WhatsApp) não encontradas nos secrets.")
        return

    # 4. Cabeçalho
    caminho_logo = os.path.join(DIRETORIO_ATUAL, "image_255acd.jpg")
    try:
        st.image(caminho_logo, width=180)
    except Exception:
        st.warning(f"Logo não encontrado em: {caminho_logo}")

    st.markdown("<h3 style='text-align: center; color: #8E163B; margin-top: -15px;'>Confirmação de Presença</h3>", unsafe_allow_html=True)
    st.write("")
    
    try:
        sheet = conectar_planilha()
        registros = sheet.get_all_records()
    except Exception as e:
        st.error(f"Erro ao conectar na planilha de registros. Detalhe: {e}")
        return

    contagem = {cat: 0 for cat in LIMITES_PRATOS.keys()}
    for r in registros:
        cat_atual = str(r.get("Categoria", "")).strip().capitalize()
        if cat_atual in contagem:
            contagem[cat_atual] += 1

    vagas_ocupadas = sum(contagem.values())

    if vagas_ocupadas >= TOTAL_VAGAS:
        st.warning("Todas as inscrições já foram preenchidas! Procure a liderança do evento para mais informações.")
        return

    # 5. Fluxo Mobile-First para o Pagamento
    st.markdown("---")
    st.markdown("<h4 style='color: #8E163B;'>Pagamento da Inscrição</h4>", unsafe_allow_html=True)
    st.write("**Valor:** R$ 20,00")
    
    st.write("Para pagar usando este celular, copie o código PIX abaixo e cole no aplicativo do seu banco:")
    # Usando a variável segura vinda dos secrets
    st.code(CHAVE_PIX)
    
    st.write("*(Ou, se preferir, escaneie o QR Code abaixo com outro aparelho)*")
    
    caminho_qr = os.path.join(DIRETORIO_ATUAL, "image_255b43.png")
    try:
        st.image(caminho_qr, width=150)
    except Exception:
        st.warning(f"QR Code não encontrado em: {caminho_qr}")

    st.markdown("---")
    st.write("Após realizar o pagamento, preencha seus dados abaixo para finalizar sua inscrição:")

    # 6. Formulário de Inscrição
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

        for idx, reg in enumerate(registros):
            tel_reg = limpar_telefone(reg.get("Telefone", ""))
            if tel_reg == tel_digitos:
                linha_existente = idx + 2
                categoria_atribuida = reg.get("Categoria")
                break

        if linha_existente:
            try:
                with st.spinner("Atualizando seus dados..."):
                    sheet.update_cell(linha_existente, 2, nome_limpo)
                
                st.info(f"Olá, {nome_limpo}! Sua inscrição já consta em nosso sistema.")
                exibir_resultado(categoria_atribuida, WHATSAPP_CONTATO)
                return
            except Exception:
                st.error("Erro ao atualizar os dados. Tente novamente.")
                return

        categorias_disponiveis = [
            cat for cat, limite in LIMITES_PRATOS.items() if contagem[cat] < limite
        ]

        if not categorias_disponiveis:
            st.warning("Desculpe, todas as inscrições já foram preenchidas! Procure a liderança do evento para mais informações.")
            return

        categoria_definida = random.choice(categorias_disponiveis)
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        try:
            with st.spinner("Registrando inscrição..."):
                sheet.append_row([agora, nome_limpo, telefone.strip(), categoria_definida])
            
            st.success(f"Inscrição confirmada com sucesso!")
            exibir_resultado(categoria_definida, WHATSAPP_CONTATO)
            st.balloons()
            
        except Exception:
            st.error("Erro ao salvar sua confirmação. Tente novamente.")

def exibir_resultado(categoria: str, whatsapp: str):
    cat = str(categoria).strip().lower()
    
    st.markdown(
        f"""
        <div style="background-color: #F8E9ED; padding: 15px; border-radius: 10px; border-left: 5px solid #8E163B; margin-top: 15px;">
            <h4 style="color: #8E163B; margin: 0; font-size: 1.1rem;">👉 No dia do evento, por gentileza, leve: <b>{cat}</b>.</h4>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.warning("📸 **Tire um print desta tela** agora para guardar a informação do item que você deverá levar!")

    # Botão de envio do comprovante com margem superior maior (margin-top: 50px)

    # numero do WhatsApp vindo dos secrets formatado para apresentação em tela - sem o 55 - (xx) xxxxx-xxxx
    whatsapp_formatado = f"({whatsapp[2:4]}) {whatsapp[4:9]}-{whatsapp[9:]}" if len(whatsapp) == 13 else whatsapp

    st.markdown(
        f"""
        <div style="margin-top: 50px; margin-bottom: 20px;">
            <p style="text-align: center; font-weight: bold; color: #333; font-size: 1.1rem;">Para concluir, envie o comprovante de pagamento clicando no botão abaixo ou para o número {whatsapp_formatado}:</p>
            <a href="https://wa.me/{whatsapp}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; text-align: center; padding: 14px; border-radius: 8px; font-weight: bold; width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    📲 Enviar Comprovante no WhatsApp
                </div>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()