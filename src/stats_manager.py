import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger(__name__)

STATS_FILE = Path("data/stats.json")
HISTORY_FILE = Path("data/email_history.json")


class StatsManager:
    """Gerencia estatísticas do sistema."""
    
    def __init__(self):
        self.stats = self.load_stats()
    
    def load_stats(self) -> Dict[str, Any]:
        """Carrega estatísticas do arquivo."""
        if STATS_FILE.exists():
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.get_default_stats()
    
    def save_stats(self):
        """Salva estatísticas no arquivo."""
        self.stats['last_updated'] = datetime.now().isoformat()
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
    
    def get_default_stats(self) -> Dict[str, Any]:
        """Retorna estrutura padrão de estatísticas."""
        return {
            "total_emails_sent": 0,
            "total_errors": 0,
            "success_rate": 100,
            "emails_by_status": {
                "success": 0,
                "error": 0,
                "pending": 0
            },
            "emails_by_month": {},
            "popular_companies": {},
            "email_templates_used": {
                "ai_generated": 0,
                "manual": 0
            },
            "ai_usage": {
                "cv_analyzed": 0,
                "emails_generated": 0
            },
            "response_times": [],
            "last_updated": None
        }
    
    def record_email_sent(self, success: bool, company_name: str | None = None, 
                          is_ai_generated: bool = True, response_time: float = 0):
        """Registra um email enviado."""
        self.stats['total_emails_sent'] += 1
        
        if success:
            self.stats['emails_by_status']['success'] += 1
        else:
            self.stats['emails_by_status']['error'] += 1
            self.stats['total_errors'] += 1
        
        # Calcular taxa de sucesso
        total = self.stats['total_emails_sent']
        successes = self.stats['emails_by_status']['success']
        self.stats['success_rate'] = round((successes / total * 100), 2) if total > 0 else 100
        
        # Registrar por mês
        month_key = datetime.now().strftime('%Y-%m')
        if month_key not in self.stats['emails_by_month']:
            self.stats['emails_by_month'][month_key] = 0
        self.stats['emails_by_month'][month_key] += 1
        
        # Empresas populares
        if company_name:
            if company_name not in self.stats['popular_companies']:
                self.stats['popular_companies'][company_name] = 0
            self.stats['popular_companies'][company_name] += 1
        
        # Tipo de template
        template_type = 'ai_generated' if is_ai_generated else 'manual'
        self.stats['email_templates_used'][template_type] += 1
        
        if is_ai_generated:
            self.stats['ai_usage']['emails_generated'] += 1
        
        # Response time
        if response_time > 0:
            self.stats['response_times'].append(response_time)
            # Manter apenas últimos 100
            self.stats['response_times'] = self.stats['response_times'][-100:]
        
        self.save_stats()
        logger.info(f"📊 Estatísticas atualizadas: {successes}/{total} sucessos ({self.stats['success_rate']}%)")
    
    def record_cv_analyzed(self):
        """Registra análise de currículo."""
        self.stats['ai_usage']['cv_analyzed'] += 1
        self.save_stats()
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo das estatísticas."""
        avg_response_time = 0
        if self.stats['response_times']:
            avg_response_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
        
        # Top 5 empresas
        top_companies = sorted(
            self.stats['popular_companies'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        # Emails por mês (últimos 6)
        sorted_months = sorted(self.stats['emails_by_month'].items())[-6:]
        
        return {
            "total_sent": self.stats['total_emails_sent'],
            "total_errors": self.stats['total_errors'],
            "success_rate": self.stats['success_rate'],
            "emails_by_status": self.stats['emails_by_status'],
            "top_companies": dict(top_companies),
            "emails_by_month": dict(sorted_months),
            "template_usage": self.stats['email_templates_used'],
            "ai_usage": self.stats['ai_usage'],
            "avg_response_time": round(avg_response_time, 2),
            "last_updated": self.stats.get('last_updated')
        }
    
    def reset_stats(self):
        """Reseta todas as estatísticas."""
        self.stats = self.get_default_stats()
        self.save_stats()
        logger.warning("⚠️ Estatísticas resetadas")
