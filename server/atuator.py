from datetime import datetime, timedelta

# estado interno para atuadores com base em tempo
_bed_presence_start = None
_bed_depression_alert_sent = False


def door_atuator(door_hangouts: int, cat_name: str = "desconhecido") -> dict:
    """Retorna alerta / ação para o atuador de porta."""
    alert = {
        "sensor": "door",
        "cat_name": cat_name,
        "door_hangouts": door_hangouts,
        "timestamp": datetime.now().isoformat(),
        "action": None,
        "message": None
    }

    if door_hangouts > 8:
        alert["action"] = "close_door"
        alert["message"] = f"O gatinho {cat_name} saiu {door_hangouts} vezes pela porta; fechando porta para segurança."  # critical
    elif door_hangouts >= 5:
        alert["message"] = f"Alerta: o gatinho {cat_name} saiu {door_hangouts} vezes pela porta. Atividade acima do normal."
    else:
        alert["message"] = None

    return alert


def window_atuator(window_hangouts: int, cat_name: str = "desconhecido") -> dict:
    alert = {
        "sensor": "window",
        "cat_name": cat_name,
        "window_hangouts": window_hangouts,
        "timestamp": datetime.now().isoformat(),
        "action": None,
        "message": None
    }

    if window_hangouts > 8:
        alert["action"] = "close_window"
        alert["message"] = f"O gatinho {cat_name} saiu {window_hangouts} vezes pela janela; fechando janela para segurança."
    elif window_hangouts >= 5:
        alert["message"] = f"Alerta: o gatinho {cat_name} saiu {window_hangouts} vezes pela janela. Atividade acima do normal."

    return alert


def food_atuator(total_of_meals: int, cat_name: str = "desconhecido") -> dict:
    alert = {
        "sensor": "food",
        "cat_name": cat_name,
        "total_of_meals": total_of_meals,
        "timestamp": datetime.now().isoformat(),
        "action": None,
        "message": None
    }

    if total_of_meals > 6:
        alert["action"] = "block_dispenser"
        alert["message"] = f"Alerta crítico: {cat_name} comeu {total_of_meals} vezes. Dispenser bloqueado (possível ansiedade)."
    elif total_of_meals > 4:
        alert["message"] = f"Alerta: {cat_name} comeu {total_of_meals} vezes. Reavaliar ração e manter observação."

    return alert


# para sandbox e cama controlamos estado temporal no servidor, mas podemos expor utilitários aqui

def sandbox_atuator(total_usage: int, cat_name: str = "desconhecido", history: list = None) -> dict:
    """Retorna alertas para uso da caixa de areia."""
    now = datetime.now()
    alert = {
        "sensor": "sandbox",
        "cat_name": cat_name,
        "total_usage": total_usage,
        "timestamp": now.isoformat(),
        "action": None,
        "message": []
    }

    alert["message"].append(
        f"Aviso: {cat_name} usou a caixa de areia ({total_usage} vezes); pode ser dor de barriga ou incontinência urinária."
    )

    if history is not None:
        one_hour_ago = now - timedelta(hours=1)
        history[:] = [t for t in history if t >= one_hour_ago]

        if len(history) <= 2:
            alert["message"].append(
                f"Aviso complementar: {cat_name} usou a caixa <=2 vezes na última hora; possível problema renal ou baixa ingestão de fibras."
            )

    return alert


def bed_atuator(cat_state: bool, cat_name: str = "desconhecido") -> dict:
    """Utiliza estado global para determinar possível tristeza/depressão."""
    global _bed_presence_start, _bed_depression_alert_sent

    now = datetime.now()
    alert = {
        "sensor": "bed",
        "cat_name": cat_name,
        "cat_state": cat_state,
        "timestamp": now.isoformat(),
        "action": None,
        "message": None
    }

    if cat_state:
        if _bed_presence_start is None:
            _bed_presence_start = now

        elapsed = now - _bed_presence_start
        if elapsed.total_seconds() >= 15 * 60 and not _bed_depression_alert_sent:
            alert["message"] = (
                f"Alerta: {cat_name} permaneceu na cama {elapsed.seconds // 60} minutos (simulado 20h). Pode estar triste/depressivo; estimule brincadeiras."
            )
            _bed_depression_alert_sent = True
            alert["action"] = "cat_mood_check"

    else:
        _bed_presence_start = None
        _bed_depression_alert_sent = False

    return alert
