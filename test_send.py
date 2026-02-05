"""
Script de teste: Envia email com resumo inteligente + currículo anexado
"""
import os
from src.email_system import EmailSender
from src.cv_analyzer import PDFAnalyzer

def main():
    print("\n🚀 Iniciando teste de envio de email...\n")
    
    # Configurações
    cv_path = "Curriculo_Theodoro.pdf"
    profile_path = "data/user_profile.json"
    test_email = "victorgft@outlook.com"
    
    # Verificar se currículo existe
    if not os.path.exists(cv_path):
        print(f"❌ Currículo não encontrado: {cv_path}")
        return
    
    # Verificar se perfil existe
    if not os.path.exists(profile_path):
        print(f"❌ Perfil não encontrado: {profile_path}")
        return
    
    # Carregar perfil
    import json
    with open(profile_path, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    print(f"✅ Perfil carregado: {profile['name']}")
    print(f"✅ Currículo encontrado: {cv_path}\n")
    
    # Gerar resumo inteligente usando Gemini
    print("🤖 Gerando resumo inteligente do currículo...\n")
    analyzer = PDFAnalyzer()
    
    # Contexto para o email de apresentação
    job_context = {
        "company_name": "Tech Company (Teste)",
        "job_title": "Desenvolvedor Fullstack",
        "job_description": "Vaga para desenvolvedor com experiência em desenvolvimento web, mobile e desktop."
    }
    
    subject, html_body = analyzer.generate_email_html(profile, job_context)
    
    print(f"📌 Assunto: {subject}")
    print(f"📏 HTML gerado: {len(html_body)} caracteres\n")
    
    # Enviar email com anexo
    print(f"📧 Enviando para: {test_email}...\n")
    sender = EmailSender()
    
    success = sender.send_html_email(
        to_address=test_email,
        subject=subject,
        html_body=html_body,
        attachments=[cv_path]
    )
    
    if success:
        print("\n✅ EMAIL ENVIADO COM SUCESSO!")
        print(f"   📬 Destinatário: {test_email}")
        print(f"   📎 Anexo: {cv_path}")
        print(f"   🤖 Com resumo inteligente gerado por IA")
    else:
        print("\n❌ Falha no envio do email")

if __name__ == "__main__":
    main()
