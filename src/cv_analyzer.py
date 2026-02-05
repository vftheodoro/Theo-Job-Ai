import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any

import google.generativeai as genai
import PyPDF2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """Analisa currículos em PDF usando Gemini."""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        logger.info("✅ PDFAnalyzer inicializado")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extrai texto de um arquivo PDF."""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                logger.info(f"📄 Lendo PDF: {num_pages} página(s)")
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    logger.info(f"   ✓ Página {page_num}/{num_pages} extraída")
            
            logger.info(f"✅ Texto extraído: {len(text)} caracteres")
            return text.strip()
        
        except Exception as e:
            logger.error(f"❌ Erro ao extrair texto do PDF: {e}")
            raise
    
    def analyze_resume(self, pdf_path: str) -> Dict[str, Any]:
        """Analisa currículo e extrai informações estruturadas usando Gemini."""
        logger.info("🤖 Iniciando análise inteligente do currículo...")
        
        # Extrair texto do PDF
        resume_text = self.extract_text_from_pdf(pdf_path)
        
        # Prompt para análise estruturada
        prompt = f"""
Você é um especialista em análise de currículos. Analise o currículo abaixo e extraia TODAS as informações relevantes em formato JSON.

CURRÍCULO:
{resume_text}

Retorne um JSON válido com a seguinte estrutura (preencha com as informações encontradas):
{{
    "name": "Nome completo da pessoa",
    "email": "Email principal",
    "phone": "Telefone com código de área",
    "title": "Cargo/título profissional atual ou desejado",
    "linkedin": "URL completa do LinkedIn (se encontrada)",
    "github": "URL completa do GitHub (se encontrada)",
    "portfolio": "URL do portfólio ou site pessoal (se encontrada)",
    "summary": "Resumo profissional ou objetivo de 2-3 frases",
    "skills": ["lista", "de", "todas", "as", "habilidades", "técnicas", "encontradas"],
    "experience_years": número_estimado_de_anos_de_experiência,
    "languages": ["idiomas que a pessoa fala"],
    "education": [
        {{
            "degree": "Título do curso",
            "institution": "Nome da instituição",
            "year": "Ano de conclusão ou período"
        }}
    ],
    "experience": [
        {{
            "title": "Cargo",
            "company": "Empresa",
            "period": "Período",
            "description": "Descrição breve"
        }}
    ],
    "certifications": ["Lista de certificações se houver"],
    "location": "Cidade/Estado/País se mencionado"
}}

IMPORTANTE:
- Se algum campo não for encontrado, use null
- Para skills, extraia TODAS as tecnologias, ferramentas, frameworks mencionados
- Para redes sociais, procure por URLs completas (linkedin.com/in/..., github.com/...)
- Seja preciso e completo
- Retorne APENAS o JSON, sem texto adicional
"""
        
        try:
            response = self.model.generate_content(prompt)
            json_text = response.text.strip()
            
            # Extrair JSON do texto (remover markdown se houver)
            json_match = re.search(r'\{[\s\S]*\}', json_text)
            if json_match:
                json_text = json_match.group(0)
            
            profile_data = json.loads(json_text)
            logger.info("✅ Currículo analisado com sucesso")
            logger.info(f"   📝 Nome: {profile_data.get('name')}")
            logger.info(f"   💼 Cargo: {profile_data.get('title')}")
            logger.info(f"   🔧 Skills encontradas: {len(profile_data.get('skills', []))}")
            
            return profile_data
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON da resposta do Gemini: {e}")
            logger.error(f"Resposta recebida: {json_text[:500]}...")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao analisar currículo: {e}")
            raise
    
    def generate_email_html(
        self,
        profile: Dict[str, Any],
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        job_description: Optional[str] = None
    ) -> tuple[str, str]:
        """Gera email HTML completo e bonito usando Gemini."""
        logger.info("🎨 Gerando email HTML com IA...")
        
        # Preparar contexto
        context = f"""
PERFIL DO CANDIDATO:
Nome: {profile.get('name')}
Cargo Atual: {profile.get('title')}
Email: {profile.get('email')}
Telefone: {profile.get('phone')}
LinkedIn: {profile.get('linkedin')}
GitHub: {profile.get('github')}
Resumo: {profile.get('summary')}
Skills principais: {', '.join(profile.get('skills', [])[:10])}
Anos de experiência: {profile.get('experience_years')}
Idiomas: {', '.join(profile.get('languages', []))}
"""
        
        if company_name:
            context += f"\nEMPRESA ALVO: {company_name}"
        if job_title:
            context += f"\nVAGA: {job_title}"
        if job_description:
            context += f"\nDESCRIÇÃO DA VAGA:\n{job_description}"
        
        prompt = f"""
Você é um profissional experiente escrevendo um email de candidatura simples e direto.

{context}

Crie um email HTML SIMPLES e HUMANO de candidatura que seja:

1. CONTEÚDO (ESSENCIAL):
   - Tom conversacional e profissional, como se fosse escrito por uma pessoa real
   - Assunto direto e objetivo (ex: "Candidatura para [Vaga] - [Nome]")
   - Cumprimento simples e educado
   - 2-3 parágrafos curtos explicando:
     * Quem você é e o que faz
     * Por que se interessa pela vaga/empresa
     * Principais qualificações relevantes (sem exagero)
   - Encerramento natural pedindo retorno
   - Máximo 150 palavras no total

2. DESIGN (MINIMALISTA):
   - HTML simples e limpo - SEM gradientes, SEM cores chamativas
   - Fundo branco, texto preto/cinza escuro
   - Fonte padrão (Arial, Helvetica, sans-serif)
   - Apenas negrito para destacar pontos importantes
   - NO máximo uma linha separadora simples
   - Footer discreto com contatos (sem ícones exagerados)
   - SEM badges, SEM tags coloridas, SEM emojis no corpo

3. TOM:
   - Natural e humano, não corporativo demais
   - Demonstre interesse genuíno, não desesperado
   - Confiante mas não arrogante
   - Como se você estivesse conversando pessoalmente

Retorne no seguinte formato JSON:
{{
    "subject": "Assunto simples e direto",
    "html_body": "HTML minimalista e profissional"
}}

IMPORTANTE:
- Menos é mais - seja direto e objetivo
- Evite clichês corporativos e linguagem robótica
- Se não houver vaga específica, faça uma candidatura espontânea simples
- Retorne APENAS o JSON válido, sem markdown
"""
        
        try:
            response = self.model.generate_content(prompt)
            json_text = response.text.strip()
            
            # Extrair JSON
            json_match = re.search(r'\{[\s\S]*\}', json_text)
            if json_match:
                json_text = json_match.group(0)
            
            email_data = json.loads(json_text)
            
            subject = email_data.get('subject', f"Candidatura - {profile.get('name')}")
            html_body = email_data.get('html_body', '')
            
            logger.info("✅ Email HTML gerado com sucesso")
            logger.info(f"   📌 Assunto: {subject}")
            logger.info(f"   📏 Tamanho HTML: {len(html_body)} caracteres")
            
            return subject, html_body
        
        except Exception as e:
            logger.error(f"❌ Erro ao gerar email HTML: {e}")
            raise


def process_resume_and_create_profile(pdf_path: str, save_path: str = "data/user_profile.json") -> Dict[str, Any]:
    """Processa currículo em PDF e cria perfil automaticamente."""
    logger.info("=" * 80)
    logger.info("🚀 PROCESSANDO CURRÍCULO COM IA")
    logger.info("=" * 80)
    
    try:
        analyzer = PDFAnalyzer()
        profile_data = analyzer.analyze_resume(pdf_path)
        
        # Salvar perfil
        save_dir = Path(save_path).parent
        save_dir.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"✅ Perfil salvo em: {save_path}")
        logger.info("=" * 80)
        
        return profile_data
    
    except Exception as e:
        logger.error(f"❌ Erro ao processar currículo: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Teste
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python cv_analyzer.py <caminho_do_curriculo.pdf>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    profile = process_resume_and_create_profile(pdf_file)
    
    print("\n✅ Perfil extraído:")
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    
    # Testar geração de email
    print("\n🎨 Gerando email de teste...")
    analyzer = PDFAnalyzer()
    subject, html = analyzer.generate_email_html(
        profile,
        company_name="Google",
        job_title="Software Engineer"
    )
    print(f"\n📌 Assunto: {subject}")
    print(f"📏 HTML gerado: {len(html)} caracteres")
