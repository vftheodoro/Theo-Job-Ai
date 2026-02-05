# -*- coding: utf-8 -*-
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class AssistantIA:
    """Assistente IA para ajudar usuário com configurações e sugestões."""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY nao encontrada no .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        logger.info("[ASSISTANT] Inicializado")
    
    def suggest_template(self, profile: Dict[str, Any]) -> str:
        """Sugere um template de email baseado no perfil do usuário."""
        logger.info("[ASSISTANT] Gerando sugestao de template...")
        
        prompt = f"""
Voce eh um especialista em recrutamento ajudando alguem a criar um template de email de candidatura.

PERFIL DO USUARIO:
- Nome: {profile.get('name')}
- Cargo: {profile.get('title')}
- Experiencia: {profile.get('experience_years')} anos
- Skills: {', '.join(profile.get('skills', [])[:10])}
- Localizacao: {profile.get('location')}
- Email: {profile.get('email')}
- LinkedIn: {profile.get('linkedin')}

Crie um template EXCELENTE e PROFISSIONAL de email de candidatura que:

1. ESTRUTURA:
   - Comeco forte e personalizado
   - Corpo com 2-3 pontos principais
   - Encerramento confiante
   - Maximo 150 palavras

2. TOM:
   - Confiante mas humilde
   - Demonstre interesse genuino
   - Mostrar valor, nao pedir oportunidade
   - Personalizavel com variaveis

3. VARIAVEIS A USAR:
   [COMPANY] - nome da empresa
   [JOB_TITLE] - cargo da vaga
   [SKILLS] - habilidades principais
   [EXPERIENCE] - anos de experiencia
   [NAME] - nome do usuario

RETORNE APENAS o template (sem explicacoes adicionais), pronto para usar.
"""
        
        try:
            response = self.model.generate_content(prompt)
            template = response.text.strip()
            logger.info("[ASSISTANT] Template sugerido com sucesso")
            return template
        except Exception as e:
            logger.error(f"[ASSISTANT] Erro ao sugerir template: {e}")
            raise
    
    def help_with_config(self, question: str, current_config: Dict[str, Any]) -> str:
        """Responde perguntas sobre configuracoes do sistema."""
        logger.info(f"[ASSISTANT] Respondendo pergunta: {question[:50]}...")
        
        prompt = f"""
Voce eh um assistente inteligente para o sistema "Theo Job AI" que ajuda usuarios a configurar emails de candidatura automaticos.

CONFIGURACAO ATUAL DO USUARIO:
- Modelo IA: {current_config.get('ai_model')}
- Tom do email: {current_config.get('email_tone')}
- Tamanho maximo: {current_config.get('max_email_length')} palavras
- Usar emojis: {current_config.get('use_emojis')}
- Auto-anexar CV: {current_config.get('auto_attach_cv')}

PERGUNTA DO USUARIO:
{question}

REGRAS:
- Responda de forma clara e concisa
- De sugestoes praticas
- Seja amigavel e profissional
- Se a pergunta for sobre template, recomende variacoes
- Se for sobre configuracao, explique os trade-offs
- Maximo 300 palavras

RESPONDA AGORA:
"""
        
        try:
            response = self.model.generate_content(prompt)
            answer = response.text.strip()
            logger.info("[ASSISTANT] Resposta gerada com sucesso")
            return answer
        except Exception as e:
            logger.error(f"[ASSISTANT] Erro ao responder: {e}")
            raise
    
    def improve_template(self, current_template: str, feedback: str) -> str:
        """Melhora um template existente baseado em feedback."""
        logger.info("[ASSISTANT] Melhorando template...")
        
        prompt = f"""
Voce eh um especialista em emails de candidatura. Um usuario quer melhorar seu template de email.

TEMPLATE ATUAL:
{current_template}

FEEDBACK DO USUARIO:
{feedback}

Baseado no feedback, MELHORE o template mantendo:
- A estrutura geral
- As variaveis [COMPANY], [JOB_TITLE], etc
- Maximo 150 palavras
- Tom profissional mas humano

RETORNE APENAS o template melhorado.
"""
        
        try:
            response = self.model.generate_content(prompt)
            improved = response.text.strip()
            logger.info("[ASSISTANT] Template melhorado")
            return improved
        except Exception as e:
            logger.error(f"[ASSISTANT] Erro ao melhorar: {e}")
            raise
    
    def suggest_optimization(self, stats: Dict[str, Any]) -> str:
        """Sugere otimizacoes baseadas em estatisticas."""
        logger.info("[ASSISTANT] Analisando estatisticas...")
        
        prompt = f"""
Voce eh um especialista em estrategia de candidaturas. Analise estas estatisticas:

ESTATISTICAS:
- Total de emails: {stats.get('total_sent', 0)}
- Taxa de sucesso: {stats.get('success_rate', 100)}%
- Erros: {stats.get('total_errors', 0)}
- Top empresas: {json.dumps(stats.get('top_companies', {}), ensure_ascii=False)}
- CVs analisados: {stats.get('ai_usage', {}).get('cv_analyzed', 0)}

Com base nisso, SUGIRA:
1. Uma otimizacao no template (breve)
2. Uma mudanca de configuracao recomendada
3. Uma estrategia para melhorar resultados

Seja conciso (max 200 palavras) e pratico.
"""
        
        try:
            response = self.model.generate_content(prompt)
            suggestion = response.text.strip()
            logger.info("[ASSISTANT] Sugestoes geradas")
            return suggestion
        except Exception as e:
            logger.error(f"[ASSISTANT] Erro ao sugerir: {e}")
            raise
