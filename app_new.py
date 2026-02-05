import json
import logging
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from src.email_system import send_ai_generated_email, EmailSender
from src.cv_analyzer import process_resume_and_create_profile, PDFAnalyzer

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
        "signature_template": "standard"
    }

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
    <title>Job AI - Sistema Inteligente de Candidaturas</title>
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
            🚀 Job AI
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
                <a href="?page=profile" class="nav-link {{ 'active' if page == 'profile' else '' }}">
                    👤 Meu Perfil
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

        <!-- Profile Page -->
        {% if page == 'profile' %}
        <div class="page-header">
            <h1>Meu Perfil</h1>
            <p>Gerencie suas informações profissionais</p>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <div class="card-header">📤 Atualizar Currículo</div>
                <form action="/upload-resume" method="post" enctype="multipart/form-data">
                    <div class="form-group">
                        <label class="form-label">Upload de Currículo (PDF)</label>
                        <input type="file" name="resume" accept=".pdf" class="form-input" required>
                        <small class="form-help">
                            A IA vai extrair automaticamente: nome, contatos, skills, experiências e redes sociais
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
                {% else %}
                <p style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    Nenhum perfil cadastrado ainda<br>
                    Faça upload do seu currículo
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
                <button type="submit" class="btn btn-success btn-block">
                    💾 Salvar Configurações
                </button>
            </div>
        </form>
        {% endif %}
    </div>
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
        
        # Processar
        profile_data = process_resume_and_create_profile(filepath)
        
        return redirect(f'/?page=profile&message=✅ Perfil de {profile_data.get("name")} atualizado! {len(profile_data.get("skills", []))} skills encontradas&message_type=success')
    
    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return redirect(f'/?page=profile&message=❌ Erro: {str(e)}&message_type=error')


@app.route('/send-email', methods=['POST'])
def send_email():
    """Enviar email com IA."""
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
            return redirect('/?page=send&message=❌ Email obrigatório&message_type=error')
        
        # Enviar
        cv_path = "Curriculo_Theodoro.pdf" if attach_cv and os.path.exists("Curriculo_Theodoro.pdf") else None
        
        success = send_ai_generated_email(
            to_address=to_email,
            profile_data=profile_data,
            company_name=company_name,
            job_title=job_title,
            job_description=job_description,
            cv_attachment=cv_path
        )
        
        # Salvar no histórico
        save_to_history({
            "to_email": to_email,
            "company_name": company_name,
            "job_title": job_title,
            "status": "success" if success else "error"
        })
        
        if success:
            return redirect(f'/?page=send&message=✅ Email enviado para {to_email}!&message_type=success')
        else:
            return redirect(f'/?page=send&message=❌ Falha no envio&message_type=error')
    
    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return redirect(f'/?page=send&message=❌ Erro: {str(e)}&message_type=error')


@app.route('/save-config', methods=['POST'])
def save_config_route():
    """Salvar configurações."""
    try:
        config = {
            "ai_model": request.form.get('ai_model'),
            "email_tone": request.form.get('email_tone'),
            "max_email_length": int(request.form.get('max_email_length', 150)),
            "use_emojis": request.form.get('use_emojis') == 'on',
            "auto_attach_cv": request.form.get('auto_attach_cv') == 'on',
        }
        
        save_config(config)
        return redirect('/?page=config&message=✅ Configurações salvas!&message_type=success')
    
    except Exception as e:
        return redirect(f'/?page=config&message=❌ Erro: {str(e)}&message_type=error')


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 JOB AI - Sistema Inteligente de Candidaturas")
    print("="*60)
    print(f"📍 Acesse: http://localhost:5000")
    print(f"🤖 IA: Análise de CV e geração automática de emails")
    print(f"⚙️  Configurável: Tom, estilo e modelo de IA")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
