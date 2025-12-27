"""
Background Tasks - Tarefas periódicas em background

Implementa scheduler para executar tarefas de manutenção:
- Cleanup de sessões expiradas
- Logging de estatísticas
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from .session_store import cleanup_expired_sessions

# Logger
logger = logging.getLogger(__name__)

# Scheduler global
_scheduler: AsyncIOScheduler | None = None

def get_scheduler() -> AsyncIOScheduler:
    """
    Retorna scheduler (singleton)

    Returns:
        AsyncIOScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler

def session_cleanup_task():
    """
    Task periódica: cleanup de sessões expiradas

    Com Redis, sessões expiram automaticamente via TTL.
    Esta task apenas loga estatísticas úteis.
    """
    try:
        count = cleanup_expired_sessions()
        logger.info(f"[Background Task] Session cleanup completado. Sessões ativas: {count}")
    except Exception as e:
        logger.error(f"[Background Task] Erro no cleanup de sessões: {e}")

def start_background_tasks():
    """
    Inicia todas as background tasks

    Chamada automaticamente no startup da aplicação
    """
    scheduler = get_scheduler()

    # Task 1: Cleanup de sessões a cada 30 minutos
    scheduler.add_job(
        session_cleanup_task,
        trigger=IntervalTrigger(minutes=30),
        id="session_cleanup",
        name="Cleanup de sessões expiradas",
        replace_existing=True
    )

    # Iniciar scheduler
    scheduler.start()
    logger.info("[Background Tasks] Scheduler iniciado com sucesso")
    logger.info("[Background Tasks] - session_cleanup: a cada 30 minutos")

def stop_background_tasks():
    """
    Para todas as background tasks

    Chamada automaticamente no shutdown da aplicação
    """
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("[Background Tasks] Scheduler parado com sucesso")
