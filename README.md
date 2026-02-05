# 🚀 Theo Job AI - Sistema Inteligente de Candidaturas

Sistema completo de envio automático de emails de candidatura com análise inteligente de currículos usando IA Gemini.

## ✨ Funcionalidades

### 🤖 Análise Inteligente de CV
- Upload de PDF
- Extração automática de dados (nome, skills, experiência, redes sociais)
- Perfil editável manualmente

### 📧 Envio de Emails com IA
- Geração automática de emails personalizados
- Tom configurável (formal, casual, confiante)
- Anexo automático de CV
- SMTP via Gmail

### 📊 Sistema de Estatísticas Completo
- Dashboard com métricas em tempo real
- Taxa de sucesso de envios
- Top 5 empresas
- Gráficos mensais
- Rastreamento de uso da IA
- Tempo médio de resposta
- **[Ver documentação completa](STATISTICS.md)**

### ⚙️ Configurações Avançadas
- Modelo de IA (Gemini)
- Tom do email
- Tamanho máximo
- Uso de emojis
- Auto-anexar CV

### 📝 Histórico de Envios
- Últimos 100 emails
- Status (sucesso/erro)
- Empresa e vaga
- Data/hora

## 🚀 Como Usar

### 1. Configurar Credenciais Gmail
1. Ative 2FA em [myaccount.google.com/security](https://myaccount.google.com/security)
2. Vá em **Senhas de app** (App passwords)
3. Selecione "Mail" e "Windows Computer"
4. Copie a senha gerada

### 2. Obter API Key do Gemini
1. Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Crie uma nova chave
3. Copie a API key

### 3. Configurar .env
```bash
cp .env.example .env
# Edite .env:
GMAIL_ADDRESS=seu.email@gmail.com
GMAIL_APP_PASSWORD=senha_app_aqui
GEMINI_API_KEY=sua_chave_aqui
```

### 4. Instalar Dependências
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5. Iniciar Sistema
```bash
python app.py
```

Acesse: **http://localhost:5000**

## 📖 Páginas do Sistema

### Dashboard (/)
Visão geral com cards de estatísticas rápidas

### Enviar Email (?page=send)
Formulário para envio de emails com IA:
- Email destinatário
- Nome da empresa (opcional)
- Título da vaga (opcional)
- Descrição da vaga (opcional)
- Anexar CV (checkbox)

### Histórico (?page=history)
Tabela com últimos 100 emails enviados

### Estatísticas (?page=stats)
Dashboard completo com:
- Cards de métricas
- Gráficos de status
- Uso da IA
- Top empresas
- Análise mensal
- Controles de gerenciamento

### Meu Perfil (?page=profile)
Visualização do perfil extraído do CV:
- Upload de novo CV
- Botão para edição manual

### Editar Perfil (?page=edit)
Formulário completo para edição manual de todos os campos

### Configurações IA (?page=config)
Painel de configuração:
- Modelo de IA
- Tom do email
- Tamanho máximo
- Usar emojis
- Auto-anexar CV

## 🔌 API Endpoints

### GET /api/stats
Retorna estatísticas em JSON

### POST /api/stats/reset
Reseta todas as estatísticas

## 📁 Estrutura de Dados

```
data/
  ├── user_profile.json      # Perfil extraído/editado
  ├── app_config.json         # Configurações da IA
  ├── email_history.json      # Histórico (últimos 100)
  └── stats.json              # Estatísticas completas

logs/
  └── email_sender_*.log      # Logs por dia

uploads/
  └── *.pdf                   # CVs enviados
```

## 🛠️ Tecnologias

- **Backend**: Flask 3.1.2
- **IA**: Google Gemini (models/gemini-flash-lite-latest)
- **PDF**: PyPDF2 3.0.1
- **Email**: Gmail SMTP + TLS
- **Frontend**: HTML/CSS/JS (embarcado)

## 📊 Sistema de Estatísticas

O sistema rastreia automaticamente:
- ✅ Total de emails enviados
- ✅ Taxa de sucesso (%)
- ✅ Total de erros
- ✅ Emails por status (sucesso/erro/pendente)
- ✅ Top 5 empresas mais contatadas
- ✅ Emails enviados por mês
- ✅ CVs analisados pela IA
- ✅ Emails gerados pela IA
- ✅ Tempo médio de resposta (ms)

**[📖 Documentação completa das estatísticas](STATISTICS.md)**

## 🎯 Próximas Funcionalidades

- [ ] Gráficos avançados com Chart.js
- [ ] Exportação de estatísticas (CSV/Excel)
- [ ] Sistema de follow-up automático
- [ ] Templates de email customizáveis
- [ ] Agendamento de envios
- [ ] Notificações por email
- [ ] Integração com LinkedIn
- [ ] Busca automática de vagas

## ⚠️ Notas Importantes

1. **Segurança**: Arquivo `.env` é ignorado pelo git
2. **API Key**: Não compartilhe sua chave Gemini
3. **Limite de Envios**: Gmail limita ~500 emails/dia
4. **Backup**: Faça backup regular da pasta `data/`

## 🐛 Troubleshooting

### Email não envia
- Verifique credenciais no `.env`
- Confirme que 2FA está ativo
- Teste com email pessoal primeiro

### IA não gera email
- Verifique API key do Gemini
- Veja logs em `logs/email_sender_*.log`
- Teste modelo em [aistudio.google.com](https://aistudio.google.com)

### Estatísticas não atualizam
- Verifique permissões na pasta `data/`
- Acesse `/api/stats` para ver dados brutos
- Clique em "🔄 Atualizar Dados"

## 📝 Licença

Projeto pessoal - Uso livre

---

**Theo Job AI** - Desenvolvido com ❤️ para facilitar sua busca por emprego
