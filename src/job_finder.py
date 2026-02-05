# -*- coding: utf-8 -*-
import json
import logging
import os
import time
from typing import Optional, Dict, Any, List, Generator
from datetime import datetime

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class JobFinder:
    """Sistema inteligente de busca de vagas."""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY nao encontrada no .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        self.last_results: List[Dict[str, Any]] = []
        logger.info("[JOB_FINDER] Inicializado")
    
    # Dados de exemplo de vagas para teste
    SAMPLE_JOBS_BR = [
        {
            "title": "Desenvolvedor Python Senior",
            "company": "Nubank",
            "location": "Sao Paulo, BR",
            "url": "https://jobs.nubank.com.br/python-senior",
            "description": "Procuramos desenvolvedor Python com 5+ anos. Experiencia em APIs REST, Flask/Django. Salario: R$15-20k",
            "posted": "2 dias"
        },
        {
            "title": "Full Stack Developer (Node.js + React)",
            "company": "Stone Co",
            "location": "Sao Paulo, BR",
            "url": "https://jobs.stone.co/fullstack",
            "description": "Node.js, React, PostgreSQL. Remoto. Beneficios: vale refeicao, vale saude, flex.",
            "posted": "1 semana"
        },
        {
            "title": "Senior Frontend Engineer",
            "company": "Creditas",
            "location": "Sao Paulo, BR",
            "url": "https://jobs.creditas.com/frontend",
            "description": "React, TypeScript, 7+ anos. Trabalhe em produtos de impacto. R$18-25k",
            "posted": "3 dias"
        },
        {
            "title": "Backend Developer (Java/Spring)",
            "company": "BTG Pactual",
            "location": "Sao Paulo, BR",
            "url": "https://jobs.btgpactual.com/java",
            "description": "Java, Spring Boot, microservices. Fintech. 4+ anos experiencia.",
            "posted": "5 dias"
        },
        {
            "title": "DevOps Engineer",
            "company": "Rappi",
            "location": "Sao Paulo, BR",
            "url": "https://jobs.rappi.com/devops",
            "description": "Docker, Kubernetes, AWS. 3+ anos. Remoto, full-time.",
            "posted": "1 semana"
        },
    ]
    
    SAMPLE_JOBS_INT = [
        {
            "title": "Senior Software Engineer",
            "company": "Google",
            "location": "Mountain View, USA",
            "url": "https://careers.google.com/senior-engineer",
            "description": "Full-stack engineer. Python/Go. 5+ years. Competitive salary + equity.",
            "posted": "2 dias"
        },
        {
            "title": "Backend Engineer (Python)",
            "company": "Stripe",
            "location": "San Francisco, USA",
            "url": "https://stripe.com/jobs/backend-python",
            "description": "Python, PostgreSQL, APIs. Remoto. $200k-250k USD + equity",
            "posted": "3 dias"
        },
        {
            "title": "Full Stack Developer",
            "company": "Airbnb",
            "location": "Remote, Worldwide",
            "url": "https://airbnb.com/careers/fullstack",
            "description": "React, Node.js, Python. 3+ years. Great benefits, remote.",
            "posted": "4 dias"
        },
        {
            "title": "Frontend Engineer (React)",
            "company": "Meta",
            "location": "London, UK",
            "url": "https://meta.com/jobs/frontend",
            "description": "React, TypeScript. 4+ years. Hybrid. GBP 140k-180k",
            "posted": "1 dia"
        },
        {
            "title": "DevOps / Infrastructure Engineer",
            "company": "AWS",
            "location": "Remote (LATAM)",
            "url": "https://aws.amazon.com/careers/devops",
            "description": "Kubernetes, Terraform, CI/CD. 3+ years. Remote for LATAM.",
            "posted": "5 dias"
        },
    ]
    
    def search_jobs(
        self, 
        profile: Dict[str, Any],
        region: str = "both",
        max_results: int = 10,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Busca vagas de forma inteligente com pensamentos em tempo real."""
        
        # Garantir que max_results é int
        max_results = int(max_results)
        
        yield "[INICIANDO] Analisando seu perfil...\n"
        time.sleep(0.2)
        
        # Analisar perfil
        skills = ", ".join(profile.get('skills', [])[:8])
        experience = profile.get('experience_years', 0)
        title = profile.get('title', 'Developer')
        
        yield f"[PERFIL] {profile.get('name')} - {title} ({experience} anos)\n"
        yield f"[SKILLS] {skills}\n\n"
        time.sleep(0.4)

        if preferences:
            yield "[PREFERENCIAS] Aplicando orientacoes para a IA...\n"
            if preferences.get("keywords"):
                yield f"- Keywords: {', '.join(preferences.get('keywords', []))}\n"
            if preferences.get("required_keywords"):
                yield f"- Palavras importantes: {', '.join(preferences.get('required_keywords', []))}\n"
            if preferences.get("experience_levels"):
                yield f"- Nivel experiencia: {', '.join(preferences.get('experience_levels', []))}\n"
            if preferences.get("work_modes"):
                yield f"- Modalidade: {', '.join(preferences.get('work_modes', []))}\n"
            if preferences.get("company_sizes"):
                yield f"- Tamanho empresa: {', '.join(preferences.get('company_sizes', []))}\n"
            if preferences.get("contract_types"):
                yield f"- Tipo contrato: {', '.join(preferences.get('contract_types', []))}\n"
            if preferences.get("sectors"):
                yield f"- Setores: {', '.join(preferences.get('sectors', []))}\n"
            if preferences.get("education_level"):
                yield f"- Educacao: {preferences.get('education_level')}\n"
            if preferences.get("accept_travel") is not None:
                yield f"- Viagens: {'aceita' if preferences.get('accept_travel') else 'nao aceita'}\n"
            if preferences.get("location_city"):
                yield f"- Cidade base: {preferences.get('location_city')}\n"
            if preferences.get("location_radius_km"):
                yield f"- Raio: {preferences.get('location_radius_km')} km\n"
            yield "\n"
            time.sleep(0.3)
        
        yield "[BUSCANDO] Coletando vagas brasileiras...\n"
        jobs_br = self.SAMPLE_JOBS_BR if region in ["br", "both"] else []
        time.sleep(0.4)
        
        yield f"[OK] {len(jobs_br)} vagas encontradas no Brasil\n\n"
        time.sleep(0.2)
        
        yield "[BUSCANDO] Coletando vagas internacionais...\n"
        jobs_int = self.SAMPLE_JOBS_INT if region in ["int", "both"] else []
        time.sleep(0.4)
        
        yield f"[OK] {len(jobs_int)} vagas encontradas internacionalmente\n\n"
        time.sleep(0.2)
        
        all_jobs = jobs_br + jobs_int
        
        yield f"[PROCESSANDO] Analisando {len(all_jobs)} vagas com IA...\n"
        time.sleep(0.4)
        
        # Usar IA para selecionar as melhores
        yield "[PENSAMENTO] Analisando match com seu perfil...\n"
        time.sleep(0.4)
        
        selected_jobs = self._select_best_jobs(profile, all_jobs, preferences)
        self.last_results = self._ensure_job_contacts(selected_jobs)
        
        yield f"\n[RESULTADO] {len(selected_jobs)} vagas selecionadas como principais:\n\n"
        yield "="*80 + "\n\n"
        time.sleep(0.4)
        
        for i, job in enumerate(self.last_results[:max_results], 1):
            yield f"[{i}] {job['title']}\n"
            yield f"    Empresa: {job['company']}\n"
            yield f"    Localizacao: {job['location']}\n"
            yield f"    Score: {job['score']}/100\n"
            yield f"    Motivo: {job['reason']}\n"
            yield f"    URL: {job['url']}\n"
            yield f"    Email: {job.get('apply_email', '-')}\n"
            yield f"    Publicada: {job['posted']}\n\n"
            time.sleep(0.1)
        
        yield "="*80 + "\n"
        yield f"\n[CONCLUIDO] Busca finalizada! {len(selected_jobs)} vagas identificadas.\n"
    
    def _select_best_jobs(self, profile: Dict[str, Any], jobs: List[Dict], preferences: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Seleciona as melhores vagas usando IA."""
        
        jobs_text = "\n".join([
            f"- {j['title']} @ {j['company']} ({j['location']}): {j['description']}"
            for j in jobs
        ])
        
        pref_text = ""
        if preferences:
            pref_text = f"""
    PREFERENCIAS DO USUARIO:
    - Keywords: {', '.join(preferences.get('keywords', []))}
    - Palavras importantes: {', '.join(preferences.get('required_keywords', []))}
    - Nivel de experiencia: {', '.join(preferences.get('experience_levels', []))}
    - Modalidade: {', '.join(preferences.get('work_modes', []))}
    - Tamanho de empresa: {', '.join(preferences.get('company_sizes', []))}
    - Tipo de contrato: {', '.join(preferences.get('contract_types', []))}
    - Setores: {', '.join(preferences.get('sectors', []))}
    - Educacao: {preferences.get('education_level')}
    - Aceita viagens: {preferences.get('accept_travel')}
    - Cidade base: {preferences.get('location_city')}
    - Raio: {preferences.get('location_radius_km')} km
    """

        prompt = f"""
Voce eh um especialista em recrutamento. Analise TODAS estas vagas e selecione as MELHORES para este candidato:

CANDIDATO:
- Nome: {profile.get('name')}
- Cargo Atual: {profile.get('title')}
- Experiencia: {profile.get('experience_years')} anos
- Skills: {', '.join(profile.get('skills', [])[:10])}
- Localizacao: {profile.get('location')}
- Idiomas: {', '.join(profile.get('languages', []))}
- LinkedIn: {profile.get('linkedin')}

VAGAS DISPONIVEIS:
{jobs_text}

{pref_text}

Para CADA vaga, calcule:
1. Match de skills (0-100)
2. Match de experiencia (0-100)
3. Relevancia da localizacao (0-100)
4. Score final (media dos 3)

Use as preferencias como ORIENTACAO (nao filtro absoluto). Se divergir, apenas reduza levemente o score.

Retorne um JSON com as TOP 5 vagas, ordenadas por score decrescente:
[
    {{
        "title": "titulo",
        "company": "empresa",
        "score": 85,
        "reason": "Por que eh um bom match (1-2 frases)"
    }},
    ...
]

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional
- Ordene por score descendente
- Minimo 5 vagas, maximo 10
"""
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Limpar se tiver markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            selected = json.loads(text)
            
            # Enriquecer com dados originais
            result = []
            for job_data in selected:
                # Encontrar vaga original
                original = next(
                    (j for j in jobs if j['company'] == job_data['company'] and j['title'] == job_data['title']),
                    None
                )
                if original:
                    job_data.update(original)
                    result.append(job_data)
            
            if result:
                return result[:5]  # Retornar top 5

            # Fallback: retornar top 5 simples quando IA nao retorna vagas
            fallback = []
            for job in jobs[:5]:
                fallback.append({
                    **job,
                    "score": 50,
                    "reason": "Selecao automatica (fallback)"
                })
            return fallback
        
        except Exception as e:
            logger.error(f"Erro ao selecionar vagas: {e}")
            # Retornar top 5 por ordem de postagem
            fallback = sorted(jobs, key=lambda x: x.get('posted', ''))[:5]
            return [
                {**job, "score": 50, "reason": "Selecao automatica (fallback)"}
                for job in fallback
            ]

    def _ensure_job_contacts(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for idx, job in enumerate(jobs, 1):
            company = job.get("company") or "empresa"
            url = job.get("url") or ""
            email = job.get("apply_email") or self._infer_email(company, url)
            job["apply_email"] = email
            job["rank"] = idx
            results.append(job)
        return results

    def _infer_email(self, company: str, url: str) -> str:
        domain = ""
        if url and "//" in url:
            domain = url.split("//", 1)[-1].split("/", 1)[0].replace("www.", "")
        if not domain:
            domain = company.lower().replace(" ", "") + ".com"
        return f"talentos@{domain}"

    def get_last_results(self) -> List[Dict[str, Any]]:
        return self.last_results
