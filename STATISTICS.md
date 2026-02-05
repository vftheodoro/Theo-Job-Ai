# 📊 Sistema de Estatísticas - Theo Job AI

## Visão Geral

O Theo Job AI agora possui um sistema completo de rastreamento de estatísticas que monitora todas as atividades do sistema, incluindo envios de emails, análises de CV, taxas de sucesso e muito mais.

## Funcionalidades

### 1. Dashboard de Estatísticas (`?page=stats`)

Acesse a página de estatísticas através do menu lateral para visualizar:

#### Cards Principais
- **Total de Emails**: Contador de todos os emails enviados
- **Taxa de Sucesso**: Percentual de emails enviados com sucesso
- **Total de Erros**: Contagem de falhas no envio
- **CVs Analisados**: Quantos currículos foram processados pela IA

#### Emails por Status
Visualização dos emails divididos por:
- ✅ Sucesso
- ❌ Erros
- ⏳ Pendentes

#### Uso da IA
Gráficos de barras mostrando:
- **CVs Analisados**: Quantos currículos foram processados
- **Emails Gerados**: Quantos emails a IA criou

#### Top 5 Empresas
Lista das empresas para as quais você mais enviou emails, útil para:
- Identificar empresas prioritárias
- Evitar duplicatas
- Análise de mercado

#### Emails por Mês
Visualização temporal dos envios, permitindo:
- Identificar períodos de maior atividade
- Planejar estratégias de candidatura
- Acompanhar progresso ao longo do tempo

### 2. API de Estatísticas

#### Endpoint: `GET /api/stats`

Retorna JSON com todas as estatísticas:

```json
{
  "total_sent": 10,
  "total_errors": 1,
  "success_rate": 90.0,
  "emails_by_status": {
    "success": 9,
    "error": 1,
    "pending": 0
  },
  "top_companies": {
    "Google": 3,
    "Microsoft": 2,
    "Amazon": 2
  },
  "emails_by_month": {
    "2025-01": 10
  },
  "template_usage": {
    "ai_generated": 10,
    "manual": 0
  },
  "ai_usage": {
    "cv_analyzed": 1,
    "emails_generated": 10
  },
  "avg_response_time": 1250.5,
  "last_updated": "2025-01-18T10:30:00"
}
```

#### Endpoint: `POST /api/stats/reset`

Reseta todas as estatísticas para valores iniciais. **Atenção**: Esta ação é irreversível!

### 3. Rastreamento Automático

O sistema rastreia automaticamente:

#### Ao Enviar Email
- ✅ Incrementa total de emails
- ✅ Registra status (sucesso/erro)
- ✅ Atualiza taxa de sucesso
- ✅ Adiciona empresa à lista
- ✅ Incrementa contador mensal
- ✅ Registra tempo de resposta
- ✅ Marca como email gerado por IA

#### Ao Analisar CV
- ✅ Incrementa contador de CVs analisados
- ✅ Atualiza estatísticas de uso da IA

### 4. Arquivo de Dados

Todas as estatísticas são salvas em: `data/stats.json`

Estrutura:
```json
{
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
  "last_updated": null
}
```

## Métricas Importantes

### Taxa de Sucesso
- **Ideal**: Acima de 95%
- **Bom**: 85-95%
- **Atenção**: Abaixo de 85%

Se sua taxa estiver baixa, verifique:
- Configurações de SMTP
- Validade dos emails destinatários
- Quota de envio do Gmail

### Tempo de Resposta
- **Rápido**: < 1000ms
- **Normal**: 1000-3000ms
- **Lento**: > 3000ms

Tempos lentos podem indicar:
- Problemas de rede
- API do Gemini sobrecarregada
- CV muito grande

### CVs Analisados vs Emails Enviados

O ideal é que você envie múltiplos emails por cada CV analisado, reutilizando o perfil extraído.

Proporção recomendada: **1 CV : 10+ Emails**

## Boas Práticas

1. **Monitore Regularmente**: Acesse a página de estatísticas semanalmente
2. **Analise Erros**: Se houver muitos erros, investigue as causas
3. **Diversifique Empresas**: Não envie muitos emails para a mesma empresa
4. **Mantenha Ritmo**: Distribua envios ao longo do mês
5. **Backup**: Faça backup do arquivo `data/stats.json` periodicamente

## Resetar Estatísticas

Para começar do zero:

1. Acesse `?page=stats`
2. Clique em "🗑️ Resetar Estatísticas"
3. Confirme a ação

**Atenção**: Esta ação é permanente e não pode ser desfeita!

## Integrações Futuras

Recursos planejados:
- 📈 Gráficos avançados com Chart.js
- 📧 Relatórios por email
- 📊 Exportação para CSV/Excel
- 🔔 Alertas de taxa de sucesso baixa
- 📅 Metas e objetivos de envio
- 🎯 Análise de conversão (respostas recebidas)

## Suporte

Para dúvidas ou problemas:
1. Verifique os logs em `logs/email_sender_YYYYMMDD.log`
2. Teste a API: `curl http://localhost:5000/api/stats`
3. Valide o arquivo `data/stats.json`

---

**Theo Job AI** - Sistema Inteligente de Candidaturas 🚀
