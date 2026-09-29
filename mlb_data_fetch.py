"""
mlb_data_fetch.py

Primer modulo automatizado del "Departamento de datos" del bot de MLB.
Conecta con la MLB Stats API (publica, sin necesidad de API key) para traer
el calendario del dia, pitchers probables y records de cada equipo.

Requiere:  pip install requests
Ejecutar:  python mlb_data_fetch.py [YYYY-MM-DD]
Si no se pasa fecha, usa el dia de hoy.
"""

import os
import sys
from datetime import date
from typing import Optional

import requests

BASE_URL = "https://statsapi.mlb.com/api/v1/schedule"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def get_todays_games(target_date: Optional[str] = None) -> list[dict]:
    """Trae los juegos de MLB para una fecha dada (YYYY-MM-DD).

    Devuelve una lista de diccionarios ya procesados con:
    equipo local, equipo visitante, pitchers probables, records y estado.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    params = {
        "sportId": 1,
        "date": target_date,
        "hydrate": "team,linescore,probablePitcher",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error al conectar con la MLB Stats API: {e}")
        return []

    data = response.json()
    games = []

    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            games.append(_parse_game(game))

    return games


def _parse_game(game: dict) -> dict:
    """Extrae solo los campos que nos interesan de un juego crudo de la API."""
    teams = game.get("teams", {})
    home = teams.get("home", {})
    away = teams.get("away", {})

    return {
        "hora_utc": game.get("gameDate"),
        "estado": game.get("status", {}).get("detailedState"),
        "local": home.get("team", {}).get("name"),
        "local_record": _format_record(home.get("leagueRecord")),
        "visitante": away.get("team", {}).get("name"),
        "visitante_record": _format_record(away.get("leagueRecord")),
        "pitcher_local": home.get("probablePitcher", {}).get("fullName", "No anunciado"),
        "pitcher_visitante": away.get("probablePitcher", {}).get("fullName", "No anunciado"),
    }


def _format_record(record: Optional[dict]) -> str:
    if not record:
        return "N/D"
    return f"{record.get('wins', '?')}-{record.get('losses', '?')}"


def print_games(games: list[dict]) -> None:
    if not games:
        print("No se encontraron juegos para esta fecha.")
        return

    for g in games:
        print("-" * 60)
        print(f"{g['visitante']} ({g['visitante_record']}) @ {g['local']} ({g['local_record']})")
        print(f"Estado: {g['estado']}")
        print(f"Pitcher visitante: {g['pitcher_visitante']}")
        print(f"Pitcher local:     {g['pitcher_local']}")


def format_games_message(games: list[dict]) -> str:
    """Arma el mismo contenido de print_games pero como un solo string,
    listo para mandarse como mensaje de Telegram."""
    if not games:
        return "No se encontraron juegos para esta fecha."

    lineas = []
    for g in games:
        lineas.append(
            f"{g['visitante']} ({g['visitante_record']}) @ "
            f"{g['local']} ({g['local_record']})\n"
            f"Estado: {g['estado']}\n"
            f"Pitcher visitante: {g['pitcher_visitante']}\n"
            f"Pitcher local: {g['pitcher_local']}"
        )
    return "\n\n".join(lineas)


def send_telegram_message(text: str) -> None:
    """Envia el mensaje al chat de Telegram configurado.

    Si no hay token o chat_id configurados (variables de entorno
    TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID), simplemente no hace nada:
    asi el script sigue funcionando en local sin Telegram.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("(Telegram no configurado, se omite el envio)")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error al enviar mensaje de Telegram: {e}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    juegos = get_todays_games(target)
    print_games(juegos)
    send_telegram_message(format_games_message(juegos))
