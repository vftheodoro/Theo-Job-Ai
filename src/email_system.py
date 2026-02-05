import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from jinja2 import Template

from src.cv_analyzer import PDFAnalyzer

# Configurar logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"email_sender_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class UserProfile:
    """Gerencia o perfil do usuário."""
    
    def __init__(self, profile_path: str = "data/user_profile.json"):
        self.profile_path = Path(profile_path)
        self.data = self.load_profile()
    
    def load_profile(self) -> dict:
        """Carrega perfil do usuário do arquivo JSON."""
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                logger.info(f"✅ Perfil carregado: {profile.get('name', 'Desconhecido')}")
                return profile
        except FileNotFoundError:
            logger.error(f"❌ Arquivo de perfil não encontrado: {self.profile_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON: {e}")
            return {}
    
    def get(self, key: str, default=None):
        """Obtém valor do perfil."""
        return self.data.get(key, default)


class EmailSender:
    """Gerencia envio de emails via Gmail SMTP."""
    
    def __init__(self):
        load_dotenv()
        self.gmail_address = os.getenv("GMAIL_ADDRESS")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        
        if not self.gmail_address or not self.gmail_password:
            logger.error("❌ Credenciais Gmail não configuradas no .env")
            raise ValueError("Credenciais Gmail ausentes")
        
        logger.info(f"✅ EmailSender inicializado com: {self.gmail_address}")
    
    def send_html_email(
        self,
        to_address: str,
        subject: str,
        html_body: str,
        attachments: Optional[list] = None
    ) -> bool:
        """Envia email HTML."""
        try:
            logger.info(f"📧 Iniciando envio para: {to_address}")
            logger.info(f"📌 Assunto: {subject}")
            
            # Criar mensagem
            msg = MIMEMultipart("alternative")
            msg["From"] = self.gmail_address
            msg["To"] = to_address
            msg["Subject"] = subject
            
            # Anexar HTML
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            
            # Anexar arquivos
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = os.path.basename(file_path)
                            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                            msg.attach(part)
                            logger.info(f"📎 Anexo adicionado: {filename}")
                    else:
                        logger.warning(f"⚠️ Arquivo não encontrado: {file_path}")
            
            # Conectar e enviar
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email enviado com sucesso para {to_address}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Erro de autenticação Gmail - verifique credenciais")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Erro SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar email: {e}", exc_info=True)
            return False


class EmailComposer:
    """Compõe emails HTML usando templates."""
    
    def __init__(self, template_path: str = "templates/email_template.html"):
        self.template_path = Path(template_path)
        self.template = self.load_template()
    
    def load_template(self) -> Optional[Template]:
        """Carrega template HTML."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                logger.info(f"✅ Template carregado: {self.template_path}")
                return Template(template_content)
        except FileNotFoundError:
            logger.error(f"❌ Template não encontrado: {self.template_path}")
            return None
    
    def compose(
        self,
        profile: UserProfile,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        custom_intro: Optional[str] = None,
        custom_closing: Optional[str] = None
    ) -> str:
        """Compõe email HTML personalizado."""
        
        if not self.template:
            logger.error("❌ Template não disponível")
            return ""
        
        # Preparar textos
        top_skills = ", ".join(profile.get("skills", [])[:3])
        
        introduction = custom_intro or profile.get("default_introduction", "").format(
            name=profile.get("name", "Candidato"),
            experience_years=profile.get("experience_years", "X"),
            top_skills=top_skills
        )
        
        closing = custom_closing or profile.get("default_closing", "")
        
        # Contexto do template
        context = {
            "candidate_name": profile.get("name", "Candidato"),
            "candidate_email": profile.get("email", ""),
            "candidate_phone": profile.get("phone"),
            "candidate_title": profile.get("title", "Profissional"),
            "candidate_linkedin": profile.get("linkedin"),
            "candidate_github": profile.get("github"),
            "company_name": company_name,
            "job_title": job_title,
            "skills": profile.get("skills", []),
            "introduction_text": introduction,
            "closing_text": closing,
            "has_attachment": False  # TODO: implementar anexos
        }
        
        html = self.template.render(**context)
        logger.info(f"✅ Email composto para empresa: {company_name or 'Não especificada'}")
        
        return html


def send_application_email(
    to_address: str,
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
    subject: Optional[str] = None
) -> bool:
    """Função principal para enviar email de candidatura."""
    
    logger.info("=" * 80)
    logger.info("🚀 INICIANDO ENVIO DE CANDIDATURA")
    logger.info("=" * 80)
    
    try:
        # Carregar perfil
        profile = UserProfile()
        
        # Compor email
        composer = EmailComposer()
        html_body = composer.compose(
            profile=profile,
            company_name=company_name,
            job_title=job_title
        )
        
        if not html_body:
            logger.error("❌ Falha ao compor email")
            return False
        
        # Definir assunto
        if not subject:
            if company_name and job_title:
                subject = f"Candidatura para {job_title} - {profile.get('name')}"
            elif company_name:
                subject = f"Candidatura - {profile.get('name')}"
            else:
                subject = f"Candidatura Profissional - {profile.get('name')}"
        
        # Enviar
        sender = EmailSender()
        success = sender.send_html_email(to_address, subject, html_body)
        
        logger.info("=" * 80)
        if success:
            logger.info("✅ CANDIDATURA ENVIADA COM SUCESSO")
        else:
            logger.info("❌ FALHA NO ENVIO DA CANDIDATURA")
        logger.info("=" * 80)
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}", exc_info=True)
        return False


def send_ai_generated_email(
    to_address: str,
    profile_data: Dict[str, Any],
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
    job_description: Optional[str] = None
) -> bool:
    """Envia email gerado por IA baseado no perfil."""
    
    logger.info("=" * 80)
    logger.info("🤖 ENVIANDO CANDIDATURA COM EMAIL GERADO POR IA")
    logger.info("=" * 80)
    
    try:
        # Gerar email com IA
        analyzer = PDFAnalyzer()
        subject, html_body = analyzer.generate_email_html(
            profile=profile_data,
            company_name=company_name,
            job_title=job_title,
            job_description=job_description
        )
        
        # Enviar
        sender = EmailSender()
        success = sender.send_html_email(to_address, subject, html_body)
        
        logger.info("=" * 80)
        if success:
            logger.info("✅ CANDIDATURA IA ENVIADA COM SUCESSO")
        else:
            logger.info("❌ FALHA NO ENVIO")
        logger.info("=" * 80)
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Teste de envio
    send_application_email(
        to_address="victorgft@outlook.com",
        company_name="Microsoft",
        job_title="Desenvolvedor Full Stack Senior",
        subject="Candidatura para Desenvolvedor Full Stack - Victor Theodoro"
    )
