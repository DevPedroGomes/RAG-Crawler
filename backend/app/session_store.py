"""
Session Store - Gerenciamento de sessões com Redis

Implementação com Redis para persistência e escalabilidade horizontal.
TTL é gerenciado automaticamente pelo Redis usando SETEX.
"""

import secrets
import json
from typing import Optional, Dict
import redis
from .config import settings

# Cliente Redis (singleton)
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """
    Retorna cliente Redis (singleton)

    Returns:
        Cliente Redis configurado
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    return _redis_client

def create_session(user_id: str, ttl: int = 7200) -> tuple[str, str]:
    """
    Cria uma nova sessão e retorna (session_id, csrf_token)

    Args:
        user_id: ID do usuário
        ttl: Time to live em segundos (padrão: 2 horas)

    Returns:
        Tupla (session_id, csrf_token)
    """
    client = get_redis_client()
    sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(16)

    session_data = {
        "user_id": user_id,
        "csrf_token": csrf,
    }

    # SETEX atomicamente seta valor e TTL
    client.setex(
        f"session:{sid}",
        ttl,
        json.dumps(session_data)
    )

    return sid, csrf

def get_session(sid: str) -> Optional[Dict]:
    """
    Busca sessão por ID

    Args:
        sid: Session ID

    Returns:
        Dados da sessão ou None se não existir/expirada
    """
    client = get_redis_client()
    data = client.get(f"session:{sid}")

    if not data:
        return None

    try:
        return json.loads(data)
    except json.JSONDecodeError:
        # Dados corrompidos, deletar
        delete_session(sid)
        return None

def refresh_session(sid: str, ttl: int = 7200) -> bool:
    """
    Renova o TTL da sessão (sliding window)

    Args:
        sid: Session ID
        ttl: Novo TTL em segundos

    Returns:
        True se renovada, False se não existir
    """
    client = get_redis_client()
    key = f"session:{sid}"

    # Verifica se existe
    if not client.exists(key):
        return False

    # Renova TTL
    client.expire(key, ttl)
    return True

def delete_session(sid: str):
    """
    Remove sessão do store

    Args:
        sid: Session ID
    """
    client = get_redis_client()
    client.delete(f"session:{sid}")

def cleanup_expired_sessions():
    """
    Remove todas as sessões expiradas

    NOTA: Com Redis, o cleanup é automático via TTL.
    Esta função está aqui para compatibilidade e logging.
    """
    # Redis já faz cleanup automático com TTL
    # Mas podemos logar informações úteis
    client = get_redis_client()
    pattern = "session:*"

    # Scan para contar sessões ativas (não iteramos todas!)
    cursor = 0
    count = 0

    # Apenas conta sem deletar (redis já deleta automaticamente)
    while True:
        cursor, keys = client.scan(cursor, match=pattern, count=100)
        count += len(keys)
        if cursor == 0:
            break

    print(f"[Session Cleanup] {count} sessões ativas no Redis")
    return count

def get_all_sessions_for_user(user_id: str) -> list[str]:
    """
    Retorna todos os session IDs de um usuário
    Útil para logout de todas as sessões

    AVISO: Esta operação é cara (scan + get de todas as keys)
    Use apenas quando necessário

    Args:
        user_id: ID do usuário

    Returns:
        Lista de session IDs
    """
    client = get_redis_client()
    pattern = "session:*"
    matching_sids = []

    cursor = 0
    while True:
        cursor, keys = client.scan(cursor, match=pattern, count=100)

        for key in keys:
            data = client.get(key)
            if data:
                try:
                    session = json.loads(data)
                    if session.get("user_id") == user_id:
                        # Extrair SID do formato "session:SID"
                        sid = key.replace("session:", "")
                        matching_sids.append(sid)
                except json.JSONDecodeError:
                    continue

        if cursor == 0:
            break

    return matching_sids
