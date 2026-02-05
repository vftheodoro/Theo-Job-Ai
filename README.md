# Scout Tool (MVP)

Esta pasta está intencionalmente fora de `devscout/`.

## O que faz
- Envia emails via Gmail SMTP com autenticação simples (senha de app).
- Gera automaticamente assunto/corpo com Gemini (opcional via `--brief`).
- Suporta HTML ou texto puro.

## Por que Gmail?
- Simples: só precisa de email + senha de app (sem OAuth).
- Rápido de testar e configurar.
- Compatível com automação em larga escala.

## Configurar

### 1. Obter credenciais Gmail
1. Ative 2FA em [myaccount.google.com/security](https://myaccount.google.com/security)
2. Vá em **Senhas de app** (App passwords)
3. Selecione "Mail" e "Windows Computer" (ou seu SO)
4. Copie a senha gerada (15-16 caracteres, sem espaços)

### 2. Preencher `.env`
```bash
cp .env.example .env
# Edite .env e preencha:
# GMAIL_ADDRESS=seu.email@gmail.com
# GMAIL_APP_PASSWORD=senha_gerada_aqui
# GEMINI_API_KEY=sua_chave_aqui
```

## Instalar

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usar

### Envio simples
```bash
python src\gmail_mailer.py --to destino@exemplo.com --subject "Olá" --body "Corpo do email"
```

### Com Gemini (gera assunto/corpo)
```bash
python src\gmail_mailer.py --to destino@exemplo.com --brief "Seguimento sobre candidatura em Company X para vaga de Dev"
```

### Com HTML
```bash
python src\gmail_mailer.py --to destino@exemplo.com --brief "Seu contexto aqui" --html
```

### Com nome do remetente (para prompt do Gemini)
```bash
python src\gmail_mailer.py --to destino@exemplo.com --brief "Seu contexto" --sender-name "Seu Nome"
```

## Próximas etapas
- [ ] Integrar busca de vagas
- [ ] Suportar múltiplos emails (por usuário)
- [ ] Adicionar logging estruturado
- [ ] Criar endpoint HTTP para multi-usuário

## Notas
- Arquivo `.env` é ignorado pelo git (segurança).
- Primeira execução é instantânea; não há OAuth.
- Gemini é opcional; sem `--brief`, use `--subject` e `--body`.
