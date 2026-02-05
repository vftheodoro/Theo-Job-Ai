import json
import logging
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from src.email_system import send_ai_generated_email
from src.cv_analyzer import process_resume_and_create_profile

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Criar pasta de uploads
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# Configurar logging
logger = logging.getLogger(__name__)

# Template HTML da dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job AI - Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .header h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 16px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #333;
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 100px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            width: 100%;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .profile-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .profile-info strong {
            color: #667eea;
        }
        .skills-display {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .skill-badge {
            background: #667eea;
            color: white;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .log-entry {
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
        }
        .log-entry.error {
            border-left-color: #dc3545;
            background: #fff5f5;
        }
        .log-entry.success {
            border-left-color: #28a745;
            background: #f0fff4;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
        }
        .stat-item {
            text-align: center;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Job AI Dashboard</h1>
            <p>Sistema inteligente de envio de candidaturas</p>
        </div>

        {% if message %}
        <div class="alert alert-{{ message_type }}">
            {{ message }}
        </div>
        {% endif %}

        <div class="grid">
            <!-- Upload de Currículo -->
            <div class="card">
                <h2>📄 Analisar Currículo com IA</h2>
                <form action="/upload-resume" method="post" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Upload do Currículo (PDF) *</label>
                        <input type="file" name="resume" accept=".pdf" required style="padding: 8px;">
                        <small style="color: #999; display: block; margin-top: 5px;">
                            A IA vai extrair automaticamente suas informações, skills e redes sociais
                        </small>
                    </div>
                    <button type="submit" class="btn">🤖 Analisar com IA</button>
                </form>
            </div>

            <!-- Perfil do Usuário -->
            <div class="card">
                <h2>👤 Seu Perfil</h2>
                {% if profile.name %}
                <div class="profile-info">
                    <p><strong>Nome:</strong> {{ profile.name }}</p>
                    <p><strong>Email:</strong> {{ profile.email }}</p>
                    <p><strong>Cargo:</strong> {{ profile.title }}</p>
                    {% if profile.experience_years %}
                    <p><strong>Experiência:</strong> {{ profile.experience_years }} anos</p>
                    {% endif %}
                </div>
                {% if profile.linkedin or profile.github or profile.portfolio %}
                <div class="profile-info">
                    <strong>Redes Sociais:</strong><br>
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
                <div class="profile-info">
                    <strong>Skills:</strong>
                    <div class="skills-display">
                        {% for skill in profile.skills[:8] %}
                        <span class="skill-badge">{{ skill }}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
                {% else %}
                <p style="text-align: center; color: #999; padding: 40px 20px;">
                    ⬆️ Faça upload do seu currículo para começar
                </p>
                {% endif %}
            </div>
        </div>

        <!-- Enviar Candidatura -->
        {% if profile.name %}
        <div class="card">
            <h2>📧 Enviar Candidatura (Email Gerado por IA)</h2>
            <form action="/send-ai-email" method="post">
                <div class="form-group">
                    <label>Email do Destinatário *</label>
                    <input type="email" name="to_email" value="victorgft@outlook.com" required>
                </div>
                <div class="form-group">
                    <label>Nome da Empresa</label>
                    <input type="text" name="company_name" placeholder="Ex: Microsoft">
                </div>
                <div class="form-group">
                    <label>Título da Vaga</label>
                    <input type="text" name="job_title" placeholder="Ex: Desenvolvedor Full Stack Senior">
                </div>
                <div class="form-group">
                    <label>Descrição da Vaga (opcional)</label>
                    <textarea name="job_description" placeholder="Cole a descrição da vaga aqui para um email mais personalizado..."></textarea>
                </div>
                <button type="submit" class="btn">🤖 Gerar Email com IA e Enviar</button>
            </form>
        </div>
        {% endif %}

        <!-- Logs Recentes -->
        <div class="card">
            <h2>📊 Logs Recentes</h2>
            <div id="logs-container">
                {% if logs %}
                    {% for log in logs[-10:][::-1] %}
                    <div class="log-entry {{ log.type }}">
                        <strong>{{ log.time }}</strong> - {{ log.message }}
                    </div>
                    {% endfor %}
                {% else %}
                <p style="color: #999; text-align: center; padding: 20px;">
                    Nenhum log disponível ainda. Envie uma candidatura para começar!
                </p>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
"""


def read_logs() -> list:
    """Lê os últimos logs do arquivo."""
    log_dir = Path("logs")
    today = datetime.now().strftime('%Y%m%d')
    log_file = log_dir / f"email_sender_{today}.log"
    
    logs = []
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f.readlines()[-50:]:  # Últimas 50 linhas
                    if line.strip():
                        # Parse simples do log
                        parts = line.split(' - ', 3)
                        if len(parts) >= 4:
                            log_type = "success" if "✅" in line else "error" if "❌" in line else "info"
                            logs.append({
                                "time": parts[0],
                                "message": parts[3].strip(),
                                "type": log_type
                            })
        except Exception as e:
            logger.error(f"Erro ao ler logs: {e}")
    
    return logs


@app.route('/')
def index():
    """Página inicial - dashboard."""
    # Tentar carregar perfil existente
    profile_path = Path("data/user_profile.json")
    if profile_path.exists():
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        except:
            profile = {}
    else:
        profile = {}
    
    logs = read_logs()
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        profile=profile,
        logs=logs,
        message=request.args.get('message'),
        message_type=request.args.get('message_type', 'success')
    )


@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Processa upload de currículo e analisa com IA."""
    try:
        if 'resume' not in request.files:
            return redirect(url_for('index',
                                  message='❌ Nenhum arquivo enviado',
                                  message_type='error'))
        
        file = request.files['resume']
        
        if file.filename == '':
            return redirect(url_for('index',
                                  message='❌ Nenhum arquivo selecionado',
                                  message_type='error'))
        
        if not file.filename.lower().endswith('.pdf'):
            return redirect(url_for('index',
                                  message='❌ Apenas arquivos PDF são aceitos',
                                  message_type='error'))
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"📤 Arquivo recebido: {filename}")
        
        # Processar com IA
        profile_data = process_resume_and_create_profile(filepath)
        
        return redirect(url_for('index',
                              message=f'✅ Currículo de {profile_data.get("name")} analisado com sucesso! {len(profile_data.get("skills", []))} skills encontradas.',
                              message_type='success'))
    
    except Exception as e:
        logger.error(f"Erro ao processar currículo: {e}", exc_info=True)
        return redirect(url_for('index',
                              message=f'❌ Erro ao processar: {str(e)}',
                              message_type='error'))


@app.route('/send-ai-email', methods=['POST'])
def send_ai_email():
    """Envia email gerado por IA."""
    try:
        # Carregar perfil
        profile_path = Path("data/user_profile.json")
        if not profile_path.exists():
            return redirect(url_for('index',
                                  message='❌ Faça upload do seu currículo primeiro',
                                  message_type='error'))
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        to_email = request.form.get('to_email')
        company_name = request.form.get('company_name') or None
        job_title = request.form.get('job_title') or None
        job_description = request.form.get('job_description') or None
        
        if not to_email:
            return redirect(url_for('index',
                                  message='❌ Email do destinatário é obrigatório',
                                  message_type='error'))
        
        # Enviar com IA
        success = send_ai_generated_email(
            to_address=to_email,
            profile_data=profile_data,
            company_name=company_name,
            job_title=job_title,
            job_description=job_description
        )
        
        if success:
            message = f'✅ Email gerado por IA e enviado para {to_email}!'
            message_type = 'success'
        else:
            message = f'❌ Falha ao enviar email para {to_email}'
            message_type = 'error'
        
        return redirect(url_for('index', message=message, message_type=message_type))
    
    except Exception as e:
        logger.error(f"Erro no envio: {e}", exc_info=True)
        return redirect(url_for('index',
                              message=f'❌ Erro: {str(e)}',
                              message_type='error'))


@app.route('/edit-profile')
def edit_profile():
    """Página para editar perfil (TODO)."""
    return "<h1>Em breve: Edição de perfil</h1><a href='/'>Voltar</a>"


@app.route('/api/logs')
def api_logs():
    """API para obter logs em JSON."""
    return jsonify(read_logs())


if __name__ == '__main__':
    print("🚀 Iniciando Job AI Dashboard...")
    print("📍 Acesse: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
