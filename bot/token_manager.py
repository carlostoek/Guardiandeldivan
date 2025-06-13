import secrets
from datetime import timedelta

# Durations en días
DURATIONS = {
    '1d': 1,
    '1w': 7,
    '2w': 14,
    '1m': 30,
    'forever': 3650  # Aproximadamente 10 años
}


def generate_token(duration_key: str) -> tuple[str, int]:
    """Genera un token y devuelve el par (token, dias_de_duracion)."""
    duration = DURATIONS.get(duration_key, 1)
    token = secrets.token_urlsafe(8)
    return token, duration

