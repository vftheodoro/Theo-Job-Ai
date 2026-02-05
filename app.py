# -*- coding: utf-8 -*-
import json
import logging
import os
from datetime import datetime
from pathlib import Path
import time

from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session, Response, stream_with_context
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from src.email_system import send_ai_generated_email, EmailSender
from src.cv_analyzer import process_resume_and_create_profile, PDFAnalyzer
from src.stats_manager import StatsManager
from src.assistant import AssistantIA
from src.job_finder import JobFinder

load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Criar pastas necessárias
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

# Arquivo de configurações
CONFIG_FILE = Path("data/app_config.json")
HISTORY_FILE = Path("data/email_history.json")
SITE_STATE_FILE = Path("data/site_state.json")
JOBS_CACHE_FILE = Path("data/jobs_cache.json")

# Inicializar gerenciador de estatísticas
stats_manager = StatsManager()

# Inicializar assistente IA
try:
    assistant = AssistantIA()
except Exception as e:
    logger.warning(f"Assistente IA nao disponivel: {e}")
    assistant = None

# Inicializar buscador de vagas
try:
    job_finder = JobFinder()
except Exception as e:
    logger.warning(f"Job Finder nao disponivel: {e}")
    job_finder = None

def load_config():
    """Carrega configurações do app."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "ai_model": "models/gemini-flash-lite-latest",
        "email_style": "professional_casual",
        "auto_attach_cv": True,
        "max_email_length": 150,
        "use_emojis": False,
        "email_tone": "confident_humble",
        "default_sender_name": "",
        "signature_template": "standard",
        "email_template": "Caro(a) [COMPANY],\n\nEu sou um desenvolvedor apaixonado com experiência em [SKILLS]. Vi que vocês estão procurando por [JOB_TITLE] e gostaria de contribuir com meu conhecimento para o seu time.\n\nMinha experiência inclui [EXPERIENCE], e tenho vontade de trazer soluções inovadoras para seus projetos.\n\nGostaria de discutir como posso agregar valor ao seu time.\n\nAtenciosamente,\n[NAME]"
    }

def load_site_state():
    if SITE_STATE_FILE.exists():
        with open(SITE_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "app_config": {},
        "job_search_preferences": {},
        "last_resume": {
            "path": None,
            "filename": None,
            "uploaded_at": None
        },
        "profile_updated_at": None,
        "last_job_search_at": None
    }

def save_site_state(state):
    with open(SITE_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def update_site_state(updates: dict):
    state = load_site_state()
    state.update(updates)
    save_site_state(state)
    return state

def save_jobs_cache(results: list):
    payload = {
        "updated_at": datetime.now().isoformat(),
        "results": results
    }
    with open(JOBS_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

def load_jobs_cache():
    if JOBS_CACHE_FILE.exists():
        with open(JOBS_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"updated_at": None, "results": []}

def save_config(config):
    """Salva configurações."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def load_history():
    """Carrega histórico de emails."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_to_history(data):
    """Adiciona registro ao histórico."""
    history = load_history()
    history.insert(0, {
        **data,
        "timestamp": datetime.now().isoformat(),
        "id": len(history) + 1
    })
    # Manter apenas últimos 100
    history = history[:100]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# Template HTML moderno
TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Theo Job AI - Sistema Inteligente de Candidaturas</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #64748b;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        
        /* Sidebar */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 260px;
            height: 100vh;
            background: var(--card-bg);
            border-right: 1px solid var(--border);
            padding: 20px;
            overflow-y: auto;
        }
        
        .sidebar-logo {
            font-size: 24px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .sidebar-nav {
            list-style: none;
        }
        
        .nav-item {
            margin-bottom: 5px;
        }
        
        .nav-link {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            color: var(--text-muted);
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.2s;
            font-weight: 500;
        }
        
        .nav-link:hover, .nav-link.active {
            background: var(--bg);
            color: var(--primary);
        }
        
        /* Main content */
        .main-content {
            margin-left: 260px;
            padding: 30px;
            min-height: 100vh;
        }
        
        .page-header {
            margin-bottom: 30px;
        }
        
        .page-header h1 {
            font-size: 28px;
            margin-bottom: 8px;
        }
        
        .page-header p {
            color: var(--text-muted);
            font-size: 15px;
        }
        
        /* Cards */
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid var(--border);
        }
        
        .card-header {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--bg);
            display: flex;
            justify-items: space-between;
            align-items: center;
        }
        
        /* Grid */
        .grid {
            display: grid;
            gap: 20px;
        }
        
        .grid-2 { grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); }
        .grid-3 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
        
        /* Forms */
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--text);
            font-size: 14px;
        }
        
        .form-input, .form-select, .form-textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            transition: border-color 0.2s;
        }
        
        .form-input:focus, .form-select:focus, .form-textarea:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .form-textarea {
            resize: vertical;
            min-height: 100px;
        }
        
        .form-help {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 6px;
            display: block;
        }
        
        /* Buttons */
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
        }
        
        .btn-primary {
            background: var(--primary);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--primary-dark);
        }
        
        .btn-secondary {
            background: var(--secondary);
            color: white;
        }
        
        .btn-success {
            background: var(--success);
            color: white;
        }
        
        .btn-block {
            width: 100%;
            justify-content: center;
        }
        
        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 14px;
            color: var(--text-muted);
        }
        
        /* Profile info */
        .profile-badge {
            display: inline-block;
            padding: 6px 12px;
            background: var(--bg);
            border-radius: 6px;
            font-size: 13px;
            margin: 4px;
            color: var(--text);
        }
        
        .profile-section {
            padding: 15px;
            background: var(--bg);
            border-radius: 8px;
            margin-bottom: 15px;
        }
        
        .profile-section strong {
            display: block;
            margin-bottom: 8px;
            color: var(--primary);
        }
        
        /* Alert */
        .alert {
            padding: 14px 18px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
        }
        
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #6ee7b7;
        }
        
        .alert-error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }
        
        /* Table */
        .table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .table th {
            text-align: left;
            padding: 12px;
            background: var(--bg);
            font-weight: 600;
            font-size: 13px;
            color: var(--text-muted);
            border-bottom: 2px solid var(--border);
        }
        
        .table td {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }
        
        .table tr:hover {
            background: var(--bg);
        }
        
        /* Badge */
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-success {
            background: #d1fae5;
            color: #065f46;
        }
        
        .badge-error {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .badge-pending {
            background: #fef3c7;
            color: #92400e;
        }
        
        /* Progress bar */
        .progress-bar {
            width: 100%;
            height: 10px;
            background: var(--bg);
            border-radius: 5px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), #6366f1);
            border-radius: 5px;
            transition: width 0.5s ease;
        }
        
        /* Toggle switch */
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 48px;
            height: 24px;
        }
        
        .toggle-input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--secondary);
            transition: 0.3s;
            border-radius: 24px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
        }
        
        .toggle-input:checked + .toggle-slider {
            background-color: var(--primary);
        }
        
        .toggle-input:checked + .toggle-slider:before {
            transform: translateX(24px);
        }
        
        /* Tab navigation */
        .tab-nav {
            display: flex;
            gap: 5px;
            border-bottom: 2px solid var(--border);
            margin-bottom: 20px;
        }
        
        .tab-link {
            padding: 12px 20px;
            background: none;
            border: none;
            color: var(--text-muted);
            font-weight: 500;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
        }
        
        .tab-link.active {
            color: var(--primary);
            border-bottom-color: var(--primary);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Preview box */
        .preview-box {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        /* Hidden utility */
        .hidden {
            display: none;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                transform: translateX(-100%);
            }
            
            .main-content {
                margin-left: 0;
            }
            
            .grid-2, .grid-3 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-logo">
            🚀 Theo Job AI
        </div>
        <ul class="sidebar-nav">
            <li class="nav-item">
                <a href="?page=dashboard" class="nav-link {{ 'active' if page == 'dashboard' else '' }}">
                    📊 Dashboard
                </a>
            </li>
            <li class="nav-item">
                <a href="?page=send" class="nav-link {{ 'active' if page == 'send' else '' }}">
                    📧 Nova Candidatura
                </a>
            </li>
            <li class="nav-item">
                <a href="?page=history" class="nav-link {{ 'active' if page == 'history' else '' }}">
                    📜 Histórico
                </a>
            </li>
            <li class="nav-item">
                <a href="?page=jobs" class="nav-link {{ 'active' if page == 'jobs' else '' }}">
                    🔍 Buscar Vagas
                </a>
            </li>
            <li class="nav-item">
                <a href="?page=profile" class="nav-link {{ 'active' if page == 'profile' or page == 'edit' else '' }}">
                    👤 Meu Perfil
                </a>
            </li>
            <li class="nav-item">
                <a href="?page=stats" class="nav-link {{ 'active' if page == 'stats' else '' }}">
                    📊 Estatísticas
                </a>
            </li>
            <li class="nav-item">
                <a href="?page=config" class="nav-link {{ 'active' if page == 'config' else '' }}">
                    ⚙️ Configurações IA
                </a>
            </li>
        </ul>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        {% if message %}
        <div class="alert alert-{{ message_type }}">
            <span>{{ message }}</span>
        </div>
        {% endif %}

        <!-- Dashboard Page -->
        {% if page == 'dashboard' %}
        <div class="page-header">
            <h1>Dashboard</h1>
            <p>Visão geral do seu sistema de candidaturas</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ history|length }}</div>
                <div class="stat-label">Emails Enviados</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ profile.skills|length if profile.skills else 0 }}</div>
                <div class="stat-label">Skills Cadastradas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ profile.experience_years if profile.experience_years else 0 }}</div>
                <div class="stat-label">Anos de Experiência</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ (history|selectattr('status', 'equalto', 'success')|list|length / history|length * 100)|round|int if history else 0 }}%</div>
                <div class="stat-label">Taxa de Sucesso</div>
            </div>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <div class="card-header">👤 Perfil Rápido</div>
                {% if profile.name %}
                <div class="profile-section">
                    <strong>{{ profile.name }}</strong>
                    <p>{{ profile.title }}</p>
                    <p style="color: var(--text-muted); font-size: 14px;">{{ profile.email }}</p>
                </div>
                {% if profile.skills %}
                <div style="margin-top: 15px;">
                    {% for skill in profile.skills[:6] %}
                    <span class="profile-badge">{{ skill }}</span>
                    {% endfor %}
                </div>
                {% endif %}
                <div style="margin-top: 15px;">
                    <a href="?page=profile" class="btn btn-secondary">Ver Perfil Completo →</a>
                </div>
                {% else %}
                <p style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                    Faça upload do seu currículo para começar
                </p>
                <a href="?page=profile" class="btn btn-primary btn-block">📄 Analisar Currículo</a>
                {% endif %}
            </div>

            <div class="card">
                <div class="card-header">📬 Últimos Envios</div>
                {% if history %}
                <table class="table">
                    <thead>
                        <tr>
                            <th>Destinatário</th>
                            <th>Empresa</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in history[:5] %}
                        <tr>
                            <td>{{ item.to_email }}</td>
                            <td>{{ item.company_name or '-' }}</td>
                            <td>
                                <span class="badge badge-{{ item.status }}">
                                    {{ '✓' if item.status == 'success' else '✗' }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                <div style="margin-top: 15px;">
                    <a href="?page=history" class="btn btn-secondary">Ver Todos →</a>
                </div>
                {% else %}
                <p style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                    Nenhum email enviado ainda
                </p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        <!-- Send Page -->
        {% if page == 'send' %}
        <div class="page-header">
            <h1>Nova Candidatura</h1>
            <p>Envie um email profissional gerado automaticamente por IA</p>
        </div>

        {% if not profile.name %}
        <div class="card">
            <p style="text-align: center; padding: 40px; color: var(--text-muted);">
                ⚠️ Você precisa fazer upload do seu currículo primeiro
            </p>
            <a href="?page=profile" class="btn btn-primary btn-block">Analisar Currículo Agora</a>
        </div>
        {% else %}
        <div class="card">
            <form action="/send-email" method="post" id="sendForm">
                <div class="grid grid-2">
                    <div class="form-group">
                        <label class="form-label">Email do Destinatário *</label>
                        <input type="email" name="to_email" class="form-input" required 
                               value="victorgft@outlook.com">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Nome da Empresa</label>
                        <input type="text" name="company_name" class="form-input" 
                               placeholder="Ex: Microsoft">
                        <small class="form-help">Opcional - torna o email mais personalizado</small>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Título da Vaga</label>
                    <input type="text" name="job_title" class="form-input" 
                           placeholder="Ex: Desenvolvedor Full Stack Sênior">
                </div>

                <div class="form-group">
                    <label class="form-label">Descrição da Vaga</label>
                    <textarea name="job_description" class="form-textarea" 
                              placeholder="Cole aqui a descrição da vaga para um email ainda mais personalizado..."></textarea>
                    <small class="form-help">Quanto mais detalhes, melhor a IA consegue personalizar</small>
                </div>

                <div class="grid grid-2">
                    <div class="form-group">
                        <label class="form-label">Anexar Currículo</label>
                        <label class="toggle-switch">
                            <input type="checkbox" name="attach_cv" class="toggle-input" 
                                   {{ 'checked' if config.auto_attach_cv else '' }}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary btn-block">
                    🤖 Gerar e Enviar Email com IA
                </button>
            </form>
        </div>

        <div class="card" style="margin-top: 20px;">
            <div class="card-header">ℹ️ Como Funciona</div>
            <ol style="padding-left: 20px; line-height: 2;">
                <li>A IA analisa seu perfil e a vaga informada</li>
                <li>Gera um email profissional e personalizado</li>
                <li>Envia automaticamente com seu currículo anexado</li>
                <li>Registra no histórico para acompanhamento</li>
            </ol>
        </div>
        {% endif %}
        {% endif %}

        <!-- History Page -->
        {% if page == 'history' %}
        <div class="page-header">
            <h1>Histórico de Envios</h1>
            <p>Todos os emails enviados pelo sistema</p>
        </div>

        <div class="card">
            {% if history %}
            <table class="table">
                <thead>
                    <tr>
                        <th>Data/Hora</th>
                        <th>Destinatário</th>
                        <th>Empresa</th>
                        <th>Vaga</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in history %}
                    <tr>
                        <td>{{ item.timestamp[:16] if item.timestamp else '-' }}</td>
                        <td>{{ item.to_email }}</td>
                        <td>{{ item.company_name or '-' }}</td>
                        <td>{{ item.job_title or '-' }}</td>
                        <td>
                            <span class="badge badge-{{ item.status }}">
                                {{ 'Enviado' if item.status == 'success' else 'Erro' }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="text-align: center; padding: 60px; color: var(--text-muted);">
                📭 Nenhum email enviado ainda<br>
                <a href="?page=send" style="color: var(--primary); margin-top: 10px; display: inline-block;">
                    Enviar primeiro email →
                </a>
            </p>
            {% endif %}
        </div>
        {% endif %}

        <!-- Job Search Page -->
        {% if page == 'jobs' %}
        <div class="page-header">
            <h1>Buscar Vagas</h1>
            <p>Encontre as melhores oportunidades de trabalho baseadas no seu perfil</p>
        </div>

        <div class="card" style="margin-bottom: 20px;">
            <div class="card-header">Configuracoes de Busca</div>
            <div style="padding: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Regiao</label>
                    <select id="region-filter" class="form-select">
                        <option value="both">Brasil + Internacional</option>
                        <option value="br">Apenas Brasil</option>
                        <option value="int">Apenas Internacional</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Maximas Vagas</label>
                    <input type="number" id="max-results" class="form-input" value="10" min="1" max="50">
                </div>
            </div>
            <div style="padding: 0 20px 20px;">
                <button onclick="startJobSearch(this)" class="btn" style="background: var(--primary); width: 100%;">
                    Iniciar Busca Inteligente
                </button>
            </div>
        </div>

        <div class="card" style="margin-bottom: 20px;">
            <div class="card-header">Configuracoes da IA para Buscar Vagas</div>
            <div style="padding: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Keywords (mais importante)</label>
                    <div id="keywords-tags" class="tag-input">
                        <div class="tag-container" id="keywords-container"></div>
                        <input type="text" id="keywords-input" class="tag-text" placeholder="Digite e pressione Enter">
                    </div>
                    <small class="form-help" style="display:block;">Adicione keywords como tags</small>
                    <button type="button" onclick="suggestKeywords()" class="btn" style="margin-top: 10px; background: var(--primary);">
                        Sugerir Keywords pelo Perfil
                    </button>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Palavras importantes (orienta a IA)</label>
                    <div id="required-keywords-tags" class="tag-input">
                        <div class="tag-container" id="required-keywords-container"></div>
                        <input type="text" id="required-keywords-input" class="tag-text" placeholder="Digite e pressione Enter">
                    </div>
                    <small class="form-help" style="display:block;">Use tags para destacar requisitos</small>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Nivel de Experiencia</label>
                    <div style="display:flex; gap:10px; flex-wrap: wrap;">
                        <label><input type="checkbox" class="exp-level" value="estagio"> Estagiario</label>
                        <label><input type="checkbox" class="exp-level" value="trainee"> Trainee</label>
                        <label><input type="checkbox" class="exp-level" value="junior"> Junior</label>
                        <label><input type="checkbox" class="exp-level" value="pleno"> Pleno</label>
                        <label><input type="checkbox" class="exp-level" value="senior"> Senior</label>
                        <label><input type="checkbox" class="exp-level" value="lead"> Lead</label>
                    </div>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Modalidade de Trabalho</label>
                    <div style="display:flex; gap:10px; flex-wrap: wrap;">
                        <label><input type="checkbox" class="work-mode" value="remoto"> Remoto</label>
                        <label><input type="checkbox" class="work-mode" value="hibrido"> Hibrido</label>
                        <label><input type="checkbox" class="work-mode" value="presencial"> Presencial</label>
                    </div>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Tamanho da Empresa</label>
                    <div style="display:flex; gap:10px; flex-wrap: wrap;">
                        <label><input type="checkbox" class="company-size" value="startup"> Startup</label>
                        <label><input type="checkbox" class="company-size" value="pequena"> Pequena</label>
                        <label><input type="checkbox" class="company-size" value="media"> Media</label>
                        <label><input type="checkbox" class="company-size" value="grande"> Grande</label>
                    </div>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Tipo de Contrato</label>
                    <div style="display:flex; gap:10px; flex-wrap: wrap;">
                        <label><input type="checkbox" class="contract-type" value="clt"> CLT</label>
                        <label><input type="checkbox" class="contract-type" value="pj"> PJ</label>
                        <label><input type="checkbox" class="contract-type" value="freela"> Freelancer</label>
                        <label><input type="checkbox" class="contract-type" value="estagio"> Estagio</label>
                    </div>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Nivel de Educacao</label>
                    <select id="education-level" class="form-select">
                        <option value="">Nenhum</option>
                        <option value="fundamental">Ensino Fundamental</option>
                        <option value="medio">Ensino Medio</option>
                        <option value="tecnico">Tecnico</option>
                        <option value="superior_incompleto">Superior (Incompleto)</option>
                        <option value="superior">Superior</option>
                        <option value="pos_incompleta">Pos (Incompleta)</option>
                        <option value="pos">Pos/Especializacao</option>
                        <option value="mestrado">Mestrado</option>
                        <option value="doutorado">Doutorado</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Local para Vagas Presenciais/Hibridas</label>
                    <input type="text" id="location-city" class="form-input" placeholder="Cidade base (ex: Sao Paulo)">
                    <div style="margin-top: 10px;">
                        <label style="display: block; margin-bottom: 6px; font-weight: 500;">Raio (km)</label>
                        <input type="number" id="location-radius" class="form-input" placeholder="Ex: 30" min="1" max="300">
                    </div>
                    <small class="form-help" style="display:block; margin-top: 8px;">Usado quando escolher Hibrido/Presencial</small>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Setores Preferidos</label>
                    <div id="sectors-tags" class="tag-input">
                        <div class="tag-container" id="sectors-container"></div>
                        <input type="text" id="sectors-input" class="tag-text" placeholder="Digite e pressione Enter">
                    </div>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Aceita viagens?</label>
                    <select id="accept-travel" class="form-select">
                        <option value="">Indiferente</option>
                        <option value="true">Sim</option>
                        <option value="false">Nao</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Pensamento da IA em Tempo Real</div>
            <div id="job-stream" style="padding: 20px; background: var(--bg); border-radius: 8px; min-height: 300px; max-height: 600px; overflow-y: auto; font-family: monospace; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; color: var(--text-muted);">
                Clique em "Iniciar Busca Inteligente" para ver a IA trabalhando...
            </div>
        </div>

        <style>
            .tag-input {
                background: var(--bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 8px;
                min-height: 46px;
            }
            .tag-container {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 6px;
            }
            .tag-chip {
                background: #1f2937;
                color: #fff;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 12px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }
            .tag-remove {
                cursor: pointer;
                font-weight: bold;
                opacity: 0.8;
            }
            .tag-text {
                width: 100%;
                border: none;
                outline: none;
                background: transparent;
                color: var(--text);
                font-size: 14px;
            }
        </style>

        <div id="results-container" style="margin-top: 20px; display: none;">
            <div class="card">
                <div class="card-header">Vagas Selecionadas</div>
                <div id="results-list" style="padding: 20px;">
                </div>
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function () {
                const streamDiv = document.getElementById('job-stream');
                if (streamDiv) {
                    streamDiv.innerHTML = '[PRONTO] Clique em "Iniciar Busca Inteligente" para comecar.\\n';
                }
                bindTagInput('keywords-input', 'keywords-container', tagState.keywords);
                bindTagInput('required-keywords-input', 'required-keywords-container', tagState.required_keywords);
                bindTagInput('sectors-input', 'sectors-container', tagState.sectors);
                renderTags('keywords-container', tagState.keywords);
                renderTags('required-keywords-container', tagState.required_keywords);
                renderTags('sectors-container', tagState.sectors);
                loadCachedJobPreferences();
                loadResults();
            });

            const tagState = {
                keywords: [],
                required_keywords: [],
                sectors: []
            };

            function createTag(label, onRemove) {
                const tag = document.createElement('span');
                tag.className = 'tag-chip';
                tag.textContent = label;

                const remove = document.createElement('span');
                remove.className = 'tag-remove';
                remove.textContent = '×';
                remove.onclick = onRemove;
                tag.appendChild(remove);
                return tag;
            }

            function renderTags(containerId, items) {
                const container = document.getElementById(containerId);
                if (!container) return;
                container.innerHTML = '';
                items.forEach((item, idx) => {
                    container.appendChild(createTag(item, () => {
                        items.splice(idx, 1);
                        renderTags(containerId, items);
                    }));
                });
            }

            function bindTagInput(inputId, containerId, items) {
                const input = document.getElementById(inputId);
                if (!input) return;
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ',') {
                        e.preventDefault();
                        const value = input.value.trim().replace(',', '');
                        if (value && !items.includes(value)) {
                            items.push(value);
                            renderTags(containerId, items);
                        }
                        input.value = '';
                    }
                });
            }

            async function startJobSearch(btn) {
                const region = document.getElementById('region-filter').value;
                const maxResults = document.getElementById('max-results').value;
                const streamDiv = document.getElementById('job-stream');
                const preferences = getJobPreferences();
                
                streamDiv.innerHTML = '[INICIANDO] Preparando busca...\\n';
                document.getElementById('results-container').style.display = 'none';

                if (btn) {
                    btn.disabled = true;
                    btn.textContent = 'Buscando...';
                }

                const configPayload = btoa(unescape(encodeURIComponent(JSON.stringify(preferences))));
                const url = `/api/jobs/search?region=${encodeURIComponent(region)}&max_results=${encodeURIComponent(maxResults)}&config=${encodeURIComponent(configPayload)}`;
                
                if (window.EventSource) {
                    const source = new EventSource(url);
                    let ended = false;
                    source.onmessage = function (e) {
                        try {
                            const data = JSON.parse(e.data);
                            streamDiv.innerHTML += escapeHtml(data.message);
                            streamDiv.scrollTop = streamDiv.scrollHeight;
                            if (data.message && data.message.includes('[CONCLUIDO]')) {
                                ended = true;
                                source.close();
                                if (btn) {
                                    btn.disabled = false;
                                    btn.textContent = 'Iniciar Busca Inteligente';
                                }
                                loadResults();
                            }
                        } catch (err) {}
                    };
                    source.addEventListener('end', function () {
                        ended = true;
                        source.close();
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = 'Iniciar Busca Inteligente';
                        }
                        loadResults();
                    });
                    source.onerror = function () {
                        if (ended) {
                            return;
                        }
                        streamDiv.innerHTML += '\\n[ERRO] Conexao encerrada ou perfil ausente.\\n';
                        streamDiv.scrollTop = streamDiv.scrollHeight;
                        source.close();
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = 'Iniciar Busca Inteligente';
                        }
                    };
                    return;
                }
                
                try {
                    const response = await fetch('/api/jobs/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ region: region, max_results: maxResults })
                    });

                    if (!response.ok) {
                        let errorText = 'Falha ao iniciar busca';
                        try {
                            const err = await response.json();
                            errorText = err.error || errorText;
                        } catch (e) {}
                        streamDiv.innerHTML = '\\n\\n[ERRO] ' + escapeHtml(errorText);
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = 'Iniciar Busca Inteligente';
                        }
                        return;
                    }

                    if (!response.body) {
                        streamDiv.innerHTML = '\\n\\n[ERRO] Resposta invalida do servidor';
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = 'Iniciar Busca Inteligente';
                        }
                        return;
                    }
                    
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';
                    
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        
                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\\n');
                        
                        for (let i = 0; i < lines.length - 1; i++) {
                            const line = lines[i].trim();
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.substring(6));
                                    streamDiv.innerHTML += escapeHtml(data.message);
                                    streamDiv.scrollTop = streamDiv.scrollHeight;
                                } catch (e) {}
                            }
                        }
                        buffer = lines[lines.length - 1];
                    }
                    
                    document.getElementById('results-container').style.display = 'block';
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = 'Iniciar Busca Inteligente';
                    }
                    loadResults();
                } catch (error) {
                    streamDiv.innerHTML += '\\n\\n[ERRO] ' + escapeHtml(error.message);
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = 'Iniciar Busca Inteligente';
                    }
                }
            }

            function getJobPreferences() {
                const getCheckedValues = (selector) =>
                    Array.from(document.querySelectorAll(selector + ':checked')).map(el => el.value);

                const keywords = tagState.keywords.slice();
                const requiredKeywords = tagState.required_keywords.slice();
                const sectors = tagState.sectors.slice();
                const travel = document.getElementById('accept-travel').value;
                const locationCity = document.getElementById('location-city').value.trim();
                const locationRadius = document.getElementById('location-radius').value;

                return {
                    keywords: keywords,
                    required_keywords: requiredKeywords,
                    experience_levels: getCheckedValues('.exp-level'),
                    work_modes: getCheckedValues('.work-mode'),
                    company_sizes: getCheckedValues('.company-size'),
                    contract_types: getCheckedValues('.contract-type'),
                    education_level: document.getElementById('education-level').value || null,
                    sectors: sectors,
                    accept_travel: travel === '' ? null : (travel === 'true'),
                    location_city: locationCity || null,
                    location_radius_km: locationRadius ? Number(locationRadius) : null
                };
            }

            async function suggestKeywords() {
                try {
                    const response = await fetch('/api/jobs/suggest-keywords', { method: 'GET' });
                    if (!response.ok) {
                        const err = await response.json();
                        alert(err.error || 'Falha ao sugerir keywords');
                        return;
                    }
                    const data = await response.json();
                    if (data.keywords && data.keywords.length > 0) {
                        tagState.keywords = data.keywords.slice(0, 20);
                        renderTags('keywords-container', tagState.keywords);
                    } else {
                        alert('Nenhuma keyword sugerida. Atualize seu perfil primeiro.');
                    }
                } catch (e) {
                    alert('Erro ao sugerir keywords: ' + e.message);
                }
            }

            async function loadCachedJobPreferences() {
                try {
                    const res = await fetch('/api/site-state');
                    if (!res.ok) return;
                    const state = await res.json();
                    const prefs = state.job_search_preferences || {};

                    if (prefs.keywords) {
                        tagState.keywords = prefs.keywords.slice();
                        renderTags('keywords-container', tagState.keywords);
                    }
                    if (prefs.required_keywords) {
                        tagState.required_keywords = prefs.required_keywords.slice();
                        renderTags('required-keywords-container', tagState.required_keywords);
                    }
                    if (prefs.sectors) {
                        tagState.sectors = prefs.sectors.slice();
                        renderTags('sectors-container', tagState.sectors);
                    }
                    if (prefs.education_level) {
                        document.getElementById('education-level').value = prefs.education_level;
                    }
                    if (prefs.location_city) {
                        document.getElementById('location-city').value = prefs.location_city;
                    }
                    if (prefs.location_radius_km) {
                        document.getElementById('location-radius').value = prefs.location_radius_km;
                    }
                    if (prefs.accept_travel !== null && prefs.accept_travel !== undefined) {
                        document.getElementById('accept-travel').value = prefs.accept_travel ? 'true' : 'false';
                    }

                    const setChecked = (selector, values) => {
                        if (!values) return;
                        document.querySelectorAll(selector).forEach(el => {
                            el.checked = values.includes(el.value);
                        });
                    };

                    setChecked('.exp-level', prefs.experience_levels);
                    setChecked('.work-mode', prefs.work_modes);
                    setChecked('.company-size', prefs.company_sizes);
                    setChecked('.contract-type', prefs.contract_types);
                } catch (e) {}
            }

            async function loadResults() {
                try {
                    const res = await fetch('/api/jobs/results');
                    if (!res.ok) return;
                    const data = await res.json();
                    renderResults(data.results || []);
                } catch (e) {}
            }

            function renderResults(results) {
                const container = document.getElementById('results-container');
                const list = document.getElementById('results-list');
                if (!container || !list) return;
                list.innerHTML = '';

                if (!results || results.length === 0) {
                    container.style.display = 'none';
                    return;
                }

                container.style.display = 'block';
                results.forEach((job, idx) => {
                    const card = document.createElement('div');
                    card.style.border = '1px solid var(--border-color)';
                    card.style.borderRadius = '10px';
                    card.style.padding = '16px';
                    card.style.marginBottom = '12px';
                    card.style.background = 'var(--bg)';

                    const score = job.score ?? 0;
                    const email = job.apply_email || '---';
                    const title = job.title || 'Vaga';
                    const company = job.company || 'Empresa';
                    const location = job.location || '-';
                    const reason = job.reason || job.ideal_reason || 'Match com seu perfil';
                    const url = job.url || '#';

                    card.innerHTML = `
                        <div style="display:flex; justify-content: space-between; gap: 12px; align-items: center;">
                            <div>
                                <div style="font-weight:600; font-size:15px;">${escapeHtml(title)}</div>
                                <div style="color: var(--text-muted); font-size: 13px;">${escapeHtml(company)} • ${escapeHtml(location)}</div>
                            </div>
                            <div style="background: var(--primary); color:#fff; padding:4px 10px; border-radius:999px; font-size:12px;">Score ${score}</div>
                        </div>
                        <div style="margin-top:10px; font-size:13px; color: var(--text-muted);">${escapeHtml(reason)}</div>
                        <div style="margin-top:10px; font-size:13px;">
                            <strong>Email:</strong> ${escapeHtml(email)}
                        </div>
                        <div style="margin-top:12px; display:flex; gap:10px; flex-wrap: wrap;">
                            <a href="${escapeHtml(url)}" target="_blank" class="btn" style="background: var(--primary);">Abrir Vaga</a>
                            <a href="mailto:${escapeHtml(email)}" class="btn" style="background: var(--success);">Candidatar por Email</a>
                        </div>
                    `;
                    list.appendChild(card);
                });
            }
            
            function escapeHtml(text) {
                const map = {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                };
                return text.replace(/[&<>"']/g, m => map[m]);
            }
        </script>
        {% endif %}

        <!-- Statistics Page -->
        {% if page == 'stats' %}
        <div class="page-header">
            <h1>Estatisticas do Sistema</h1>
            <p>Analise completa de envios, erros e desempenho</p>
        </div>

        <div class="grid grid-4" style="margin-bottom: 30px;">
            <div class="stat-card">
                <div class="stat-value" id="stat-total">0</div>
                <div class="stat-label">Total de Emails</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-success-rate">100%</div>
                <div class="stat-label">Taxa de Sucesso</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-errors">0</div>
                <div class="stat-label">Total de Erros</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-ai-usage">0</div>
                <div class="stat-label">CVs Analisados</div>
            </div>
        </div>

        <div class="grid grid-2" style="margin-bottom: 30px;">
            <div class="card">
                <div class="card-header">📈 Emails por Status</div>
                <div style="padding: 20px;">
                    <div style="display: flex; gap: 20px; justify-content: space-around;">
                        <div style="text-align: center;">
                            <div style="font-size: 2em; color: var(--success);" id="success-count">0</div>
                            <div style="color: var(--text-muted); font-size: 0.9em;">Sucesso</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2em; color: var(--error);" id="error-count">0</div>
                            <div style="color: var(--text-muted); font-size: 0.9em;">Erros</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2em; color: var(--warning);" id="pending-count">0</div>
                            <div style="color: var(--text-muted); font-size: 0.9em;">Pendentes</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">🤖 Uso da IA</div>
                <div style="padding: 20px;">
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>CVs Analisados</span>
                            <strong id="cv-analyzed">0</strong>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" id="cv-progress" style="width: 0%"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>Emails Gerados</span>
                            <strong id="emails-generated">0</strong>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" id="email-progress" style="width: 0%"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid grid-2" style="margin-bottom: 30px;">
            <div class="card">
                <div class="card-header">🏢 Top 5 Empresas</div>
                <div style="padding: 20px;">
                    <div id="top-companies">
                        <p style="text-align: center; color: var(--text-muted); padding: 20px;">
                            Nenhuma empresa registrada ainda
                        </p>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">📅 Emails por Mês</div>
                <div style="padding: 20px;">
                    <div id="monthly-chart">
                        <p style="text-align: center; color: var(--text-muted); padding: 20px;">
                            Nenhum dado mensal ainda
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>⚙️ Gerenciar Estatísticas</span>
                    <span id="last-updated" style="font-size: 0.85em; color: var(--text-muted);"></span>
                </div>
            </div>
            <div style="padding: 20px;">
                <div style="display: flex; gap: 15px; align-items: center;">
                    <button onclick="refreshStats()" class="btn" style="background: var(--primary);">
                        🔄 Atualizar Dados
                    </button>
                    <button onclick="resetStats()" class="btn" style="background: var(--error);">
                        🗑️ Resetar Estatísticas
                    </button>
                    <span style="color: var(--text-muted); font-size: 0.9em;">
                        Tempo médio de resposta: <strong id="avg-response">0ms</strong>
                    </span>
                </div>
            </div>
        </div>

        <script>
            // Carregar estatísticas ao entrar na página
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    // Cards principais
                    document.getElementById('stat-total').textContent = data.total_sent || 0;
                    document.getElementById('stat-success-rate').textContent = (data.success_rate || 100) + '%';
                    document.getElementById('stat-errors').textContent = data.total_errors || 0;
                    document.getElementById('stat-ai-usage').textContent = data.ai_usage?.cv_analyzed || 0;
                    
                    // Status
                    document.getElementById('success-count').textContent = data.emails_by_status?.success || 0;
                    document.getElementById('error-count').textContent = data.emails_by_status?.error || 0;
                    document.getElementById('pending-count').textContent = data.emails_by_status?.pending || 0;
                    
                    // IA Usage
                    const cvAnalyzed = data.ai_usage?.cv_analyzed || 0;
                    const emailsGenerated = data.ai_usage?.emails_generated || 0;
                    const maxAI = Math.max(cvAnalyzed, emailsGenerated, 1);
                    
                    document.getElementById('cv-analyzed').textContent = cvAnalyzed;
                    document.getElementById('emails-generated').textContent = emailsGenerated;
                    document.getElementById('cv-progress').style.width = ((cvAnalyzed / maxAI) * 100) + '%';
                    document.getElementById('email-progress').style.width = ((emailsGenerated / maxAI) * 100) + '%';
                    
                    // Top Companies
                    const topCompanies = data.top_companies || {};
                    const companiesHtml = Object.keys(topCompanies).length > 0 
                        ? Object.entries(topCompanies).map(([company, count]) => `
                            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-color);">
                                <span>${company}</span>
                                <strong>${count} emails</strong>
                            </div>
                        `).join('')
                        : '<p style="text-align: center; color: var(--text-muted); padding: 20px;">Nenhuma empresa registrada</p>';
                    document.getElementById('top-companies').innerHTML = companiesHtml;
                    
                    // Monthly Chart (simple text version)
                    const monthlyData = data.emails_by_month || {};
                    const monthlyHtml = Object.keys(monthlyData).length > 0
                        ? Object.entries(monthlyData).map(([month, count]) => {
                            const maxMonthly = Math.max(...Object.values(monthlyData));
                            const percentage = (count / maxMonthly) * 100;
                            return `
                                <div style="margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 3px;">
                                        <span>${month}</span>
                                        <strong>${count}</strong>
                                    </div>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${percentage}%"></div>
                                    </div>
                                </div>
                            `;
                        }).join('')
                        : '<p style="text-align: center; color: var(--text-muted); padding: 20px;">Nenhum dado mensal</p>';
                    document.getElementById('monthly-chart').innerHTML = monthlyHtml;
                    
                    // Metadata
                    document.getElementById('avg-response').textContent = (data.avg_response_time || 0) + 'ms';
                    if (data.last_updated) {
                        const date = new Date(data.last_updated);
                        document.getElementById('last-updated').textContent = 
                            'Última atualização: ' + date.toLocaleString('pt-BR');
                    }
                    
                } catch (error) {
                    console.error('Erro ao carregar estatísticas:', error);
                }
            }
            
            async function refreshStats() {
                await loadStats();
                alert('✅ Estatísticas atualizadas!');
            }
            
            async function resetStats() {
                if (!confirm('⚠️ Tem certeza que deseja resetar TODAS as estatísticas? Esta ação não pode ser desfeita.')) {
                    return;
                }
                
                try {
                    const response = await fetch('/api/stats/reset', { method: 'POST' });
                    if (response.ok) {
                        alert('✅ Estatísticas resetadas com sucesso!');
                        await loadStats();
                    } else {
                        alert('❌ Erro ao resetar estatísticas');
                    }
                } catch (error) {
                    alert('❌ Erro: ' + error.message);
                }
            }
            
            // Carregar ao abrir a página
            if (window.location.search.includes('page=stats')) {
                loadStats();
            }
        </script>
        {% endif %}

        <!-- Profile Page -->
        {% if page == 'profile' %}
        <div class="page-header">
            <h1>Meu Perfil</h1>
            <p>Gerencie suas informações profissionais</p>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <div class="card-header">📤 Análise Rápida com IA</div>
                <form action="/upload-resume" method="post" enctype="multipart/form-data">
                    <div class="form-group">
                        <label class="form-label">Upload de Currículo (PDF)</label>
                        <input type="file" name="resume" accept=".pdf" class="form-input" required>
                        <small class="form-help">
                            A IA extrai automaticamente suas informações. Você pode editá-las depois.
                        </small>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">
                        🤖 Analisar com IA
                    </button>
                </form>
            </div>

            <div class="card">
                <div class="card-header">👤 Perfil Atual</div>
                {% if profile.name %}
                <div class="profile-section">
                    <strong>Informações Básicas</strong>
                    <p><b>Nome:</b> {{ profile.name }}</p>
                    <p><b>Email:</b> {{ profile.email }}</p>
                    <p><b>Telefone:</b> {{ profile.phone }}</p>
                    <p><b>Cargo:</b> {{ profile.title }}</p>
                    {% if profile.experience_years %}
                    <p><b>Experiência:</b> {{ profile.experience_years }} anos</p>
                    {% endif %}
                </div>

                {% if profile.linkedin or profile.github or profile.portfolio %}
                <div class="profile-section">
                    <strong>Redes Sociais</strong>
                    {% if profile.linkedin %}
                    <p>💼 <a href="{{ profile.linkedin }}" target="_blank">LinkedIn</a></p>
                    {% endif %}
                    {% if profile.github %}
                    <p>💻 <a href="{{ profile.github }}" target="_blank">GitHub</a></p>
                    {% endif %}
                    {% if profile.portfolio %}
                    <p>🌐 <a href="{{ profile.portfolio }}" target="_blank">Portfolio</a></p>
                    {% endif %}
                </div>
                {% endif %}

                {% if profile.skills %}
                <div class="profile-section">
                    <strong>Skills ({{ profile.skills|length }})</strong>
                    <div style="margin-top: 10px;">
                        {% for skill in profile.skills %}
                        <span class="profile-badge">{{ skill }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
                
                {% if profile.name %}
                <div style="margin-top: 20px;">
                    <a href="?page=edit" class="btn btn-secondary btn-block">✏️ Editar Perfil Manualmente</a>
                </div>
                {% endif %}
                {% else %}
                <p style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    Nenhum perfil cadastrado ainda<br>
                    Faça upload do seu currículo ou <a href="?page=edit" style="color: var(--primary);">crie manualmente</a>
                </p>
                {% endif %}
            </div>
        </div>
        {% endif %}

        <!-- Config Page -->
        {% if page == 'config' %}
        <div class="page-header">
            <h1>Configurações da IA</h1>
            <p>Personalize como a IA gera seus emails de candidatura</p>
        </div>

        <form action="/save-config" method="post">
            <div class="grid grid-2">
                <div class="card">
                    <div class="card-header">🎨 Estilo do Email</div>
                    
                    <div class="form-group">
                        <label class="form-label">Tom do Email</label>
                        <select name="email_tone" class="form-select">
                            <option value="confident_humble" {{ 'selected' if config.email_tone == 'confident_humble' else '' }}>
                                Confiante mas Humilde
                            </option>
                            <option value="formal" {{ 'selected' if config.email_tone == 'formal' else '' }}>
                                Formal e Corporativo
                            </option>
                            <option value="casual" {{ 'selected' if config.email_tone == 'casual' else '' }}>
                                Casual e Amigável
                            </option>
                            <option value="enthusiastic" {{ 'selected' if config.email_tone == 'enthusiastic' else '' }}>
                                Entusiasmado
                            </option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Tamanho Máximo (palavras)</label>
                        <input type="number" name="max_email_length" class="form-input" 
                               value="{{ config.max_email_length }}" min="100" max="300">
                        <small class="form-help">Recomendado: 150 palavras para emails diretos</small>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Usar Emojis no Email</label>
                        <label class="toggle-switch">
                            <input type="checkbox" name="use_emojis" class="toggle-input" 
                                   {{ 'checked' if config.use_emojis else '' }}>
                            <span class="toggle-slider"></span>
                        </label>
                        <small class="form-help" style="display: block;">Desativado = mais profissional</small>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">⚙️ Configurações Técnicas</div>
                    
                    <div class="form-group">
                        <label class="form-label">Modelo de IA</label>
                        <select name="ai_model" class="form-select">
                            <option value="models/gemini-flash-lite-latest" {{ 'selected' if config.ai_model == 'models/gemini-flash-lite-latest' else '' }}>
                                Gemini Flash Lite (Rápido)
                            </option>
                            <option value="models/gemini-2.0-flash" {{ 'selected' if config.ai_model == 'models/gemini-2.0-flash' else '' }}>
                                Gemini 2.0 Flash (Balanceado)
                            </option>
                            <option value="models/gemini-pro-latest" {{ 'selected' if config.ai_model == 'models/gemini-pro-latest' else '' }}>
                                Gemini Pro (Qualidade Máxima)
                            </option>
                        </select>
                        <small class="form-help">Modelos mais avançados podem consumir mais quota</small>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Anexar CV Automaticamente</label>
                        <label class="toggle-switch">
                            <input type="checkbox" name="auto_attach_cv" class="toggle-input" 
                                   {{ 'checked' if config.auto_attach_cv else '' }}>
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">Template Padrao de Email</div>
                <p style="color: var(--text-muted); font-size: 0.9em; margin: 10px 0;">
                    Defina um template padrao que a IA usara como base ao gerar emails. 
                    Use [COMPANY], [JOB_TITLE], [SKILLS], [EXPERIENCE], [NAME] como variaveis.
                </p>
                
                <div class="form-group">
                    <label class="form-label">Template Padrao</label>
                    <textarea name="email_template" class="form-input" rows="10" id="email_template"
                              style="font-family: monospace; resize: vertical;">{{ config.email_template or '' }}</textarea>
                    <small class="form-help" style="display: block; margin-top: 10px;">
                        Exemplo de variaveis: [COMPANY] (empresa), [JOB_TITLE] (cargo), [SKILLS] (habilidades), [EXPERIENCE] (experiencia), [NAME] (seu nome)
                    </small>
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 15px;">
                    <button type="button" onclick="suggestTemplate()" class="btn" style="background: var(--primary); flex: 1;">
                        Gerar Sugestao da IA
                    </button>
                    <button type="button" onclick="improveTemplate()" class="btn" style="background: var(--warning); flex: 1;">
                        Melhorar com IA
                    </button>
                </div>
            </div>

            <div class="card">
                <button type="submit" class="btn btn-success btn-block">
                    Salvar Configuracoes
                </button>
            </div>
        </form>
        
        <script>
            async function suggestTemplate() {
                try {
                    const response = await fetch('/api/assistant/suggest-template', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.success) {
                        document.getElementById('email_template').value = data.template;
                        alert('[IA] Template sugerido! Verifique abaixo.');
                    } else {
                        alert('[ERRO] ' + data.error);
                    }
                } catch (error) {
                    alert('[ERRO] ' + error.message);
                }
            }
            
            async function improveTemplate() {
                const current = document.getElementById('email_template').value;
                const feedback = prompt('Como voce gostaria de melhorar o template?', 'Mais conciso, mais profissional, mais informal, etc.');
                
                if (!feedback) return;
                
                try {
                    const response = await fetch('/api/assistant/improve-template', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ template: current, feedback: feedback })
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        document.getElementById('email_template').value = data.template;
                        alert('[IA] Template melhorado!');
                    } else {
                        alert('[ERRO] ' + data.error);
                    }
                } catch (error) {
                    alert('[ERRO] ' + error.message);
                }
            }
        </script>
        {% endif %}

        <!-- Edit Profile Page -->
        {% if page == 'edit' %}
        <div class="page-header">
            <h1>Editar Perfil</h1>
            <p>Edite suas informacoes profissionais manualmente</p>
        </div>

        <form action="/save-profile" method="post">
            <div class="grid grid-2">
                <div class="card">
                    <div class="card-header">Informacoes Basicas</div>
                    
                    <div class="form-group">
                        <label class="form-label">Nome Completo *</label>
                        <input type="text" name="name" class="form-input" 
                               value="{{ profile.name or '' }}" required>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Email *</label>
                        <input type="email" name="email" class="form-input" 
                               value="{{ profile.email or '' }}" required>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Telefone</label>
                        <input type="text" name="phone" class="form-input" 
                               value="{{ profile.phone or '' }}" 
                               placeholder="+55 (00) 00000-0000">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Cargo/Título Profissional *</label>
                        <input type="text" name="title" class="form-input" 
                               value="{{ profile.title or '' }}" 
                               placeholder="Ex: Desenvolvedor Full Stack" required>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Anos de Experiência</label>
                        <input type="number" name="experience_years" class="form-input" 
                               value="{{ profile.experience_years or 0 }}" min="0" max="50">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Localização</label>
                        <input type="text" name="location" class="form-input" 
                               value="{{ profile.location or '' }}" 
                               placeholder="Cidade - Estado">
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">🌐 Redes Sociais</div>
                    
                    <div class="form-group">
                        <label class="form-label">LinkedIn</label>
                        <input type="url" name="linkedin" class="form-input" 
                               value="{{ profile.linkedin or '' }}" 
                               placeholder="https://linkedin.com/in/seu-perfil">
                    </div>

                    <div class="form-group">
                        <label class="form-label">GitHub</label>
                        <input type="url" name="github" class="form-input" 
                               value="{{ profile.github or '' }}" 
                               placeholder="https://github.com/seu-usuario">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Portfolio</label>
                        <input type="url" name="portfolio" class="form-input" 
                               value="{{ profile.portfolio or '' }}" 
                               placeholder="https://seu-portfolio.com">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Idiomas</label>
                        <input type="text" name="languages" class="form-input" 
                               value="{{ profile.languages|join(', ') if profile.languages else '' }}" 
                               placeholder="Ex: Português, Inglês, Espanhol">
                        <small class="form-help">Separe por vírgula</small>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">💼 Sobre Você</div>
                
                <div class="form-group">
                    <label class="form-label">Resumo Profissional</label>
                    <textarea name="summary" class="form-textarea" rows="4" 
                              placeholder="Descreva brevemente sua experiência e objetivos profissionais...">{{ profile.summary or '' }}</textarea>
                </div>

                <div class="form-group">
                    <label class="form-label">Skills / Habilidades</label>
                    <textarea name="skills" class="form-textarea" rows="3" 
                              placeholder="Ex: Python, JavaScript, React, Node.js, Git, AWS">{{ profile.skills|join(', ') if profile.skills else '' }}</textarea>
                    <small class="form-help">Separe por vírgula. Cada skill será exibida como badge.</small>
                </div>
            </div>

            <div class="grid grid-2">
                <a href="?page=profile" class="btn btn-secondary btn-block">← Voltar</a>
                <button type="submit" class="btn btn-success btn-block">💾 Salvar Perfil</button>
            </div>
        </form>
        {% endif %}
    </div>
    
    <!-- Assistente Flutuante - DESATIVADO -->
    <!-- <button id="assistant-btn" class="assistant-btn" onclick="toggleAssistant()">
        A
    </button> -->
    
    <!-- <div id="assistant-modal" class="assistant-modal">
        <div class="assistant-header">
            <h3>Assistente IA</h3>
            <button onclick="toggleAssistant()" class="close-btn">X</button>
        </div>
        <div id="assistant-content" class="assistant-content">
            <div style="padding: 20px; text-align: center;">
                <p style="margin-bottom: 15px;">Como posso ajudar?</p>
                <button onclick="askQuestion()" class="assistant-menu-btn">Fazer Pergunta</button>
                <button onclick="optimizeNow()" class="assistant-menu-btn">Otimizar Campanha</button>
            </div>
        </div>
    </div> -->
    
    <style>
        .assistant-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: var(--primary);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
            font-size: 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 999;
            transition: all 0.3s ease;
        }
        
        .assistant-btn:hover {
            background: var(--primary-dark);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }
        
        .assistant-modal {
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 350px;
            max-height: 500px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 40px rgba(0,0,0,0.16);
            z-index: 999;
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        
        .assistant-modal.active {
            display: flex;
        }
        
        .assistant-header {
            background: var(--primary);
            color: white;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .assistant-header h3 {
            margin: 0;
            font-size: 16px;
        }
        
        .close-btn {
            background: transparent;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 18px;
            padding: 0;
            width: 24px;
            height: 24px;
        }
        
        .assistant-content {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }
        
        .assistant-menu-btn {
            display: block;
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            background: var(--bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        
        .assistant-menu-btn:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
        
        .assistant-message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.5;
        }
        
        .assistant-message.user {
            background: var(--primary);
            color: white;
            margin-left: 20px;
        }
        
        .assistant-message.bot {
            background: var(--bg);
            margin-right: 20px;
            border: 1px solid var(--border-color);
        }
    </style>
    
    <script>
        function toggleAssistant() {
            const modal = document.getElementById('assistant-modal');
            modal.classList.toggle('active');
        }
        
        async function askQuestion() {
            const question = prompt('[ASSISTENTE]\\nO que voce gostaria de saber?\\n\\nExemplos:\\n- Como melhorar minha taxa de sucesso?\\n- Qual tom e melhor para emails?\\n- Como estruturar meu CV?');
            if (!question) return;
            
            document.getElementById('assistant-content').innerHTML = '<p style="text-align: center; color: var(--text-muted);">Processando...</p>';
            
            try {
                const response = await fetch('/api/assistant/help', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('assistant-content').innerHTML = `
                        <div class="assistant-message user">${escapeHtml(question)}</div>
                        <div class="assistant-message bot">${escapeHtml(data.answer).replace(/\n/g, '<br>')}</div>
                    `;
                } else {
                    showError(data.error);
                }
            } catch (error) {
                showError(error.message);
            }
        }
        
        async function optimizeNow() {
            document.getElementById('assistant-content').innerHTML = '<p style="text-align: center; color: var(--text-muted);">Analisando seu desempenho...</p>';
            
            try {
                const response = await fetch('/api/assistant/optimize', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('assistant-content').innerHTML = `
                        <div style="padding: 10px;">
                            <h4 style="margin-bottom: 10px;">Sugestoes de Otimizacao</h4>
                            <div class="assistant-message bot">${escapeHtml(data.suggestion).replace(/\n/g, '<br>')}</div>
                        </div>
                    `;
                } else {
                    showError(data.error);
                }
            } catch (error) {
                showError(error.message);
            }
        }
        
        function showError(error) {
            document.getElementById('assistant-content').innerHTML = `<p style="color: var(--error); padding: 15px; text-align: center;">[ERRO] ${escapeHtml(error)}</p>`;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Página principal."""
    page = request.args.get('page', 'dashboard')
    
    # Carregar dados
    config = load_config()
    history = load_history()
    
    profile_path = Path("data/user_profile.json")
    if profile_path.exists():
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
    else:
        profile = {}
    
    return render_template_string(
        TEMPLATE,
        page=page,
        profile=profile,
        config=config,
        history=history,
        message=request.args.get('message'),
        message_type=request.args.get('message_type', 'success')
    )


@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Upload e análise de currículo."""
    try:
        if 'resume' not in request.files:
            return redirect('/?page=profile&message=❌ Nenhum arquivo enviado&message_type=error')
        
        file = request.files['resume']
        
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            return redirect('/?page=profile&message=❌ Apenas arquivos PDF&message_type=error')
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        update_site_state({
            "last_resume": {
                "path": filepath,
                "filename": filename,
                "uploaded_at": datetime.now().isoformat()
            }
        })
        
        # Processar
        profile_data = process_resume_and_create_profile(filepath)
        
        # Registrar análise de CV nas estatísticas
        stats_manager.record_cv_analyzed()
        
        return redirect(f'/?page=profile&message=✅ Perfil de {profile_data.get("name")} atualizado! {len(profile_data.get("skills", []))} skills encontradas&message_type=success')
    
    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return redirect(f'/?page=profile&message=❌ Erro: {str(e)}&message_type=error')


@app.route('/send-email', methods=['POST'])
def send_email():
    """Enviar email com IA."""
    start_time = time.time()
    try:
        # Carregar perfil
        profile_path = Path("data/user_profile.json")
        if not profile_path.exists():
            return redirect('/?page=send&message=❌ Faça upload do currículo primeiro&message_type=error')
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        to_email = request.form.get('to_email')
        company_name = request.form.get('company_name') or None
        job_title = request.form.get('job_title') or None
        job_description = request.form.get('job_description') or None
        attach_cv = request.form.get('attach_cv') == 'on'
        
        if not to_email:
            return redirect('/?page=send&message=Email obrigatorio&message_type=error')
        
        # Carregar configurações para pegar template
        config = load_config()
        email_template = config.get('email_template')
        
        # Enviar
        cv_path = "Curriculo_Theodoro.pdf" if attach_cv and os.path.exists("Curriculo_Theodoro.pdf") else None
        
        success = send_ai_generated_email(
            to_address=to_email,
            profile_data=profile_data,
            company_name=company_name,
            job_title=job_title,
            job_description=job_description,
            cv_attachment=cv_path,
            email_template=email_template
        )
        
        # Calcular tempo de resposta
        response_time = round((time.time() - start_time) * 1000)  # em ms
        
        # Salvar no histórico
        save_to_history({
            "to_email": to_email,
            "company_name": company_name,
            "job_title": job_title,
            "status": "success" if success else "error"
        })
        
        # Registrar estatísticas
        stats_manager.record_email_sent(
            success=success,
            company_name=company_name,
            is_ai_generated=True,
            response_time=response_time
        )
        
        if success:
            return redirect(f'/?page=send&message=✅ Email enviado para {to_email}!&message_type=success')
        else:
            return redirect(f'/?page=send&message=❌ Falha no envio&message_type=error')
    
    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        # Registrar erro nas estatísticas
        stats_manager.record_email_sent(success=False, company_name=company_name, is_ai_generated=True)
        return redirect(f'/?page=send&message=❌ Erro: {str(e)}&message_type=error')


@app.route('/save-config', methods=['POST'])
def save_config_route():
    """Salvar configuracoes."""
    try:
        config = {
            "ai_model": request.form.get('ai_model'),
            "email_tone": request.form.get('email_tone'),
            "max_email_length": int(request.form.get('max_email_length', 150)),
            "use_emojis": request.form.get('use_emojis') == 'on',
            "auto_attach_cv": request.form.get('auto_attach_cv') == 'on',
            "email_template": request.form.get('email_template', ''),
        }
        
        save_config(config)
        update_site_state({"app_config": config})
        return redirect('/?page=config&message=Configuracoes salvas!&message_type=success')
    
    except Exception as e:
        return redirect(f'/?page=config&message=Erro: {str(e)}&message_type=error')


@app.route('/save-profile', methods=['POST'])
def save_profile():
    """Salvar perfil editado manualmente."""
    try:
        # Coletar dados do formulário
        profile_data = {
            "name": request.form.get('name'),
            "email": request.form.get('email'),
            "phone": request.form.get('phone', ''),
            "title": request.form.get('title'),
            "experience_years": int(request.form.get('experience_years', 0)),
            "location": request.form.get('location', ''),
            "linkedin": request.form.get('linkedin', ''),
            "github": request.form.get('github', ''),
            "portfolio": request.form.get('portfolio', ''),
            "summary": request.form.get('summary', ''),
            "languages": [lang.strip() for lang in request.form.get('languages', '').split(',') if lang.strip()],
            "skills": [skill.strip() for skill in request.form.get('skills', '').split(',') if skill.strip()],
        }
        
        # Remover campos vazios
        profile_data = {k: v for k, v in profile_data.items() if v}
        
        # Salvar no arquivo JSON
        profile_path = Path("data/user_profile.json")
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Perfil de {profile_data.get('name')} salvo manualmente")

        update_site_state({"profile_updated_at": datetime.now().isoformat()})
        
        return redirect('/?page=profile&message=✅ Perfil atualizado com sucesso!&message_type=success')
    
    except Exception as e:
        logger.error(f"Erro ao salvar perfil: {e}", exc_info=True)
        return redirect(f'/?page=edit&message=❌ Erro: {str(e)}&message_type=error')


@app.route('/api/stats', methods=['GET'])
def get_stats_api():
    """API endpoint para estatísticas."""
    try:
        summary = stats_manager.get_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Erro ao carregar estatísticas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats/reset', methods=['POST'])
def reset_stats_api():
    """Resetar estatísticas."""
    try:
        stats_manager.reset_stats()
        return jsonify({"success": True, "message": "Estatisticas resetadas"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/assistant/suggest-template', methods=['POST'])
def suggest_template_api():
    """Sugere template baseado no perfil."""
    try:
        if not assistant:
            return jsonify({"error": "Assistente nao disponivel"}), 503
        
        profile_path = Path("data/user_profile.json")
        if not profile_path.exists():
            return jsonify({"error": "Perfil nao encontrado"}), 404
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        template = assistant.suggest_template(profile)
        return jsonify({"template": template, "success": True})
    except Exception as e:
        logger.error(f"Erro ao sugerir template: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/assistant/help', methods=['POST'])
def assistant_help_api():
    """Assistente responde perguntas sobre configuracoes."""
    try:
        if not assistant:
            return jsonify({"error": "Assistente nao disponivel"}), 503
        
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({"error": "Pergunta nao fornecida"}), 400
        
        config = load_config()
        answer = assistant.help_with_config(question, config)
        
        return jsonify({"answer": answer, "success": True})
    except Exception as e:
        logger.error(f"Erro no assistente: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/assistant/improve-template', methods=['POST'])
def improve_template_api():
    """Melhora template existente com feedback."""
    try:
        if not assistant:
            return jsonify({"error": "Assistente nao disponivel"}), 503
        
        data = request.get_json()
        current_template = data.get('template', '')
        feedback = data.get('feedback', '')
        
        if not current_template or not feedback:
            return jsonify({"error": "Template e feedback necessarios"}), 400
        
        improved = assistant.improve_template(current_template, feedback)
        return jsonify({"template": improved, "success": True})
    except Exception as e:
        logger.error(f"Erro ao melhorar template: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/assistant/optimize', methods=['POST'])
def optimize_api():
    """Sugere otimizacoes baseadas em estatisticas."""
    try:
        if not assistant:
            return jsonify({"error": "Assistente nao disponivel"}), 503
        
        stats = stats_manager.get_summary()
        suggestion = assistant.suggest_optimization(stats)
        
        return jsonify({"suggestion": suggestion, "success": True})
    except Exception as e:
        logger.error(f"Erro ao otimizar: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs/search', methods=['GET', 'POST'])
def search_jobs_api():
    """Busca vagas com streaming de pensamentos da IA."""
    try:
        wants_stream = request.method == 'GET' or 'text/event-stream' in (request.headers.get('Accept') or '')

        if not job_finder:
            if wants_stream:
                def error_stream():
                    yield f"data: {json.dumps({'message': '[ERRO] Job Finder nao disponivel\n'})}\n\n"
                    yield "event: end\ndata: {}\n\n"
                return Response(
                    error_stream(),
                    mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
                )
            return jsonify({"error": "Job Finder nao disponivel"}), 503
        
        profile_path = Path("data/user_profile.json")
        if not profile_path.exists():
            if wants_stream:
                def error_stream():
                    yield f"data: {json.dumps({'message': '[ERRO] Perfil nao encontrado. Faca upload do CV primeiro.\n'})}\n\n"
                    yield "event: end\ndata: {}\n\n"
                return Response(
                    error_stream(),
                    mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
                )
            return jsonify({"error": "Perfil nao encontrado"}), 404
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        payload = request.get_json(silent=True) or {}
        region = payload.get('region') or request.args.get('region', 'both')  # 'br', 'int', ou 'both'
        max_results = payload.get('max_results') or request.args.get('max_results', 10)
        preferences = payload.get('preferences')

        config_b64 = request.args.get('config')
        if config_b64:
            try:
                import base64
                decoded = base64.b64decode(config_b64).decode('utf-8')
                preferences = json.loads(decoded)
            except Exception:
                preferences = preferences or None

        if preferences:
            update_site_state({
                "job_search_preferences": preferences,
                "last_job_search_at": datetime.now().isoformat()
            })
        
        def generate():
            for message in job_finder.search_jobs(profile, region, max_results, preferences):
                yield f"data: {json.dumps({'message': message})}\n\n"
            results = job_finder.get_last_results()
            save_jobs_cache(results)
            yield "event: end\ndata: {}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    
    except Exception as e:
        logger.error(f"Erro na busca de vagas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs/results', methods=['GET'])
def get_jobs_results_api():
    try:
        return jsonify(load_jobs_cache())
    except Exception as e:
        logger.error(f"Erro ao carregar resultados de vagas: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/site-state', methods=['GET'])
def get_site_state_api():
    try:
        state = load_site_state()
        return jsonify(state)
    except Exception as e:
        logger.error(f"Erro ao carregar site state: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs/suggest-keywords', methods=['GET'])
def suggest_job_keywords_api():
    """Sugere keywords com base no perfil do usuario."""
    try:
        profile_path = Path("data/user_profile.json")
        if not profile_path.exists():
            return jsonify({"error": "Perfil nao encontrado"}), 404

        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        title = profile.get('title', '')
        skills = profile.get('skills', [])

        keywords = []
        if title:
            keywords.extend([p.strip() for p in title.replace('/', ' ').split() if len(p.strip()) > 2])
        keywords.extend(skills)

        # Normalizar e limitar
        normalized = []
        for k in keywords:
            k = str(k).strip().lower()
            if k and k not in normalized:
                normalized.append(k)

        return jsonify({"keywords": normalized[:15]})
    except Exception as e:
        logger.error(f"Erro ao sugerir keywords: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("[THEO JOB AI] - Sistema Inteligente de Candidaturas")
    print("="*60)
    print(f"Acesse: http://localhost:5000")
    print(f"IA: Analise de CV e geracao automatica de emails")
    print(f"Configuravel: Tom, estilo e modelo de IA")
    print(f"Estatisticas: Contagem, sucesso e analises")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
