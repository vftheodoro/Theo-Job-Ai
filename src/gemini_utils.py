# -*- coding: utf-8 -*-
"""Utilities for Gemini API interaction with retry logic and error handling."""

import time
import logging
import json
import re
from typing import Any, Callable, Dict
from functools import wraps
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass


def retry_with_exponential_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except google_exceptions.ResourceExhausted as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"❌ API quota excedida após {max_retries} tentativas")
                        logger.error(f"   Detalhes: {str(e)}")
                        raise GeminiAPIError(
                            f"Quota da API do Gemini excedida. Por favor, aguarde alguns minutos e tente novamente. "
                            f"Erro: {str(e)}"
                        )

                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"⚠️ Quota excedida, aguardando {wait_time:.1f}s (tentativa {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                except google_exceptions.GoogleAPIError as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"❌ Erro da API após {max_retries} tentativas: {e}")
                        raise GeminiAPIError(f"Erro na API do Gemini: {str(e)}")

                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"⚠️ Erro da API, tentando novamente em {wait_time:.1f}s (tentativa {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                except Exception as e:
                    # Para outros erros, não tente novamente
                    logger.error(f"❌ Erro inesperado: {e}")
                    raise

            # Se chegou aqui, todas as tentativas falharam
            raise GeminiAPIError(f"Máximo de tentativas excedido. Último erro: {str(last_exception)}")

        return wrapper
    return decorator


@retry_with_exponential_backoff(max_retries=3)
def safe_generate_content(model: genai.GenerativeModel, prompt: str, timeout: int = 60) -> str:
    """
    Safely generate content with timeout and error handling.

    Args:
        model: Gemini model instance
        prompt: Text prompt
        timeout: Timeout in seconds

    Returns:
        Generated text

    Raises:
        GeminiAPIError: If generation fails after retries
    """
    try:
        response = model.generate_content(prompt, request_options={"timeout": timeout})

        if not response or not response.text:
            raise GeminiAPIError("API retornou resposta vazia")

        return response.text

    except AttributeError as e:
        logger.error(f"❌ Erro ao acessar resposta da API: {e}")
        raise GeminiAPIError(f"Resposta inválida da API: {str(e)}")


def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """
    Robustly extract JSON from Gemini response.
    Handles markdown code blocks, surrounding text, and various formats.

    Args:
        response_text: Raw text response from Gemini

    Returns:
        Parsed JSON as dictionary

    Raises:
        GeminiAPIError: If JSON cannot be extracted or parsed
    """
    if not response_text:
        raise GeminiAPIError("Resposta vazia da API")

    cleaned = response_text.strip()

    # Step 1: Remove markdown code blocks (```json ... ``` or ``` ... ```)
    markdown_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    markdown_match = re.search(markdown_pattern, cleaned)
    if markdown_match:
        cleaned = markdown_match.group(1).strip()
        logger.debug("JSON extraído de bloco markdown")

    # Step 2: Try to find JSON object or array
    # First try object
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        json_text = json_match.group(0)
        try:
            result = json.loads(json_text)
            logger.debug(f"✅ JSON parseado com sucesso ({len(json_text)} caracteres)")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Tentativa 1 falhou: {e}")

    # Then try array
    json_match = re.search(r'\[[\s\S]*\]', cleaned)
    if json_match:
        json_text = json_match.group(0)
        try:
            result = json.loads(json_text)
            logger.debug(f"✅ JSON array parseado com sucesso")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Tentativa 2 falhou: {e}")

    # Step 3: Try entire response as-is
    try:
        result = json.loads(cleaned)
        logger.debug("✅ JSON parseado diretamente")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"❌ Falha ao parsear JSON: {e}")
        logger.error(f"   Primeiros 200 caracteres da resposta: {response_text[:200]}")
        logger.error(f"   Últimos 200 caracteres da resposta: {response_text[-200:]}")
        raise GeminiAPIError(
            f"Não foi possível extrair JSON válido da resposta da API. "
            f"Erro: {str(e)}. Verifique os logs para mais detalhes."
        )


def validate_profile_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize profile data extracted from resume.

    Args:
        data: Raw profile data dictionary

    Returns:
        Validated and sanitized profile data
    """
    required_fields = ['name', 'email', 'skills']

    for field in required_fields:
        if field not in data or not data[field]:
            logger.warning(f"⚠️ Campo obrigatório ausente: {field}")

    # Ensure lists are actually lists
    list_fields = ['skills', 'languages', 'education', 'experience', 'certifications']
    for field in list_fields:
        if field in data and not isinstance(data[field], list):
            data[field] = []

    # Ensure experience_years is a number
    if 'experience_years' in data:
        try:
            data['experience_years'] = int(data['experience_years']) if data['experience_years'] else 0
        except (ValueError, TypeError):
            data['experience_years'] = 0

    logger.debug(f"✅ Perfil validado: {data.get('name', 'N/A')}")
    return data


def validate_email_data(data: Dict[str, Any]) -> tuple[str, str]:
    """
    Validate and extract email data from Gemini response.

    Args:
        data: Email data dictionary

    Returns:
        Tuple of (subject, html_body)

    Raises:
        GeminiAPIError: If required fields are missing
    """
    if 'subject' not in data or not data['subject']:
        raise GeminiAPIError("Email subject não encontrado na resposta da API")

    if 'html_body' not in data or not data['html_body']:
        raise GeminiAPIError("Email body não encontrado na resposta da API")

    subject = str(data['subject']).strip()
    html_body = str(data['html_body']).strip()

    if len(subject) < 5:
        raise GeminiAPIError("Subject muito curto")

    if len(html_body) < 50:
        raise GeminiAPIError("Email body muito curto")

    logger.debug(f"✅ Email validado: {len(subject)} chars (subject), {len(html_body)} chars (body)")
    return subject, html_body
