import argparse
import json
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple

import google.generativeai as genai
from dotenv import load_dotenv


def configure_gemini(api_key: str) -> None:
    if not api_key:
        print("GEMINI_API_KEY é obrigatório ao usar --brief", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=api_key)


def parse_json_like(text: str) -> Optional[dict]:
    """Tenta extrair JSON válido do texto."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def generate_email(api_key: str, brief: str, sender_name: str) -> Tuple[str, str]:
    """Usa Gemini para gerar assunto e corpo do email em português."""
    configure_gemini(api_key)
    prompt = (
        "Você é especialista em escrever emails profissionais concisos. "
        "Retorne um JSON com as chaves 'assunto' e 'corpo'. "
        "Assunto: máximo 70 caracteres. Corpo: máximo 150 palavras. "
        "Tom: profissional, amigável e claro. "
        f"Nome do remetente: {sender_name or 'Remetente'}. "
        f"Contexto/objetivo: {brief}. "
        "Responda APENAS com o JSON válido."
    )
    
    response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
    text = response.text or ""
    
    parsed = parse_json_like(text)
    if parsed and "assunto" in parsed and "corpo" in parsed:
        return parsed["assunto"].strip(), parsed["corpo"].strip()
    
    # Fallback
    return "Seguimento", text.strip() or "Olá, este é um email gerado automaticamente."


def send_email(
    gmail_address: str,
    gmail_password: str,
    to_address: str,
    subject: str,
    body: str,
    is_html: bool = False,
) -> None:
    """Envia email via Gmail SMTP."""
    try:
        # Conectar ao servidor Gmail
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_address, gmail_password)
            
            # Criar mensagem
            msg = MIMEMultipart("alternative")
            msg["From"] = gmail_address
            msg["To"] = to_address
            msg["Subject"] = subject
            
            # Adicionar corpo
            if is_html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))
            
            # Enviar
            server.send_message(msg)
            print(f"✅ Email enviado para {to_address}")
            
    except smtplib.SMTPAuthenticationError:
        print("❌ Erro: email ou senha de app inválida.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}", file=sys.stderr)
        sys.exit(1)


def get_env_value(name: str, required: bool = True) -> Optional[str]:
    """Obtém valor do arquivo .env."""
    value = os.getenv(name, "").strip()
    if required and not value:
        print(f"❌ Variável obrigatória não encontrada: {name}", file=sys.stderr)
        print(f"   Preencha o arquivo .env com o valor de {name}", file=sys.stderr)
        sys.exit(1)
    return value or None


def main() -> None:
    load_dotenv()
    
    # Obter credenciais
    gmail_address = get_env_value("GMAIL_ADDRESS", required=True)
    gmail_password = get_env_value("GMAIL_APP_PASSWORD", required=True)
    gemini_key = get_env_value("GEMINI_API_KEY", required=False)
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description="Envia email via Gmail com redação opcional por Gemini."
    )
    parser.add_argument("--to", required=True, help="Email do destinatário")
    parser.add_argument("--subject", help="Assunto do email")
    parser.add_argument("--body", help="Corpo do email em texto")
    parser.add_argument("--html", action="store_true", help="Enviar como HTML")
    parser.add_argument(
        "--brief",
        help="Se usado, Gemini gera assunto/corpo a partir deste contexto",
    )
    parser.add_argument(
        "--sender-name",
        dest="sender_name",
        default="",
        help="Seu nome (usado no prompt do Gemini)",
    )
    args = parser.parse_args()
    
    # Validar email destinatário
    to_address = (args.to or "").strip()
    if not to_address:
        print("❌ Email destinatário é obrigatório (--to)", file=sys.stderr)
        sys.exit(1)
    
    subject = args.subject or ""
    body = args.body or ""
    
    # Se --brief foi usado, gerar com Gemini
    if args.brief:
        if not gemini_key:
            print(
                "❌ GEMINI_API_KEY é obrigatória no .env para usar --brief",
                file=sys.stderr,
            )
            sys.exit(1)
        subject, body = generate_email(gemini_key, args.brief, args.sender_name)
        print(f"📝 Email gerado por Gemini:")
        print(f"   Assunto: {subject}")
        print(f"   Corpo (primeiras 100 chars): {body[:100]}...")
    
    # Valores padrão se vazios
    subject = subject or "Mensagem"
    body = body or "Olá, este é um email de teste."
    
    # Enviar
    print(f"📧 Enviando para {to_address}...")
    send_email(gmail_address, gmail_password, to_address, subject, body, args.html)


if __name__ == "__main__":
    main()
