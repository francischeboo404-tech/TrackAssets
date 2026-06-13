import time
import functools
from sqlalchemy.exc import OperationalError
from flask import current_app
from app import db


def transaction_retry(max_retries=3, backoff_factor=0.5):
    """
    Decorator to retry database transactions on transient OperationalErrors (e.g. deadlocks).
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    # Check if it's a transient error (like a deadlock or lock wait timeout)
                    # For PostgreSQL: '40P01' is deadlock, '55P03' is lock_not_available
                    # For SQLite: 'database is locked'
                    retries += 1
                    if retries >= max_retries:
                        current_app.logger.error(
                            f"Transaction failed after {max_retries} retries: {str(e)}"
                        )
                        db.session.rollback()
                        raise e

                    sleep_time = backoff_factor * (2 ** (retries - 1))
                    current_app.logger.warning(
                        f"Transient DB error ({type(e).__name__}). Retrying in {sleep_time}s... (Attempt {retries}/{max_retries})"
                    )
                    db.session.rollback()
                    time.sleep(sleep_time)
                except Exception as e:
                    # Non-transient error, don't retry
                    db.session.rollback()
                    raise e
            return func(*args, **kwargs)

        return wrapper

    return decorator
