#!/usr/bin/env python3
"""
Calibração de Zonas VDOT para Garmin MCP
==========================================

Script de entrevista que calcula as zonas de ritmo personalizadas
baseadas no resultado do último teste do corredor.

Usa as equações clássicas de Jack Daniels' Running Formula:
- VDOT = VO2 / %VO2max
- Ritmos E/T/I usam faixas de intensidade aproximadas
- M é derivado do ritmo previsto para maratona
- R usa aproximadamente 105% do VDOT

Uso:
    python calibrate_vdot.py              # Modo interativo (entrevista)
    python calibrate_vdot.py --check      # Verifica se já existe configuração
    python calibrate_vdot.py --force      # Força nova entrevita mesmo se já existir

Saída:
    Salva as zonas calculadas em vdot_zones.json na mesma pasta.
"""

import json
import sys
from datetime import date
from pathlib import Path

from app.vdot.daniels import calculate_vdot, equivalent_time, pace_for_fraction
from app.db.engine import SessionLocal
from app.db.models import VdotZoneConfig, DEFAULT_USER_ID
from app.core.config import get_settings

# Fix encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Distâncias de teste reconhecidas (em metros)
TEST_DISTANCES = {
    "1": {"name": "1500m", "meters": 1500},
    "2": {"name": "3K", "meters": 3000},
    "3": {"name": "5K", "meters": 5000},
    "4": {"name": "10K", "meters": 10000},
    "5": {"name": "Meia Maratona (21.1K)", "meters": 21097},
    "6": {"name": "Maratona (42.2K)", "meters": 42195},
    "7": {"name": "Outra distância", "meters": None},
}

# Distâncias de prova para equivalências (em km)
RACE_DISTANCES_KM = {
    "5K": 5.0,
    "10K": 10.0,
    "Meia Maratona": 21.0975,
    "Maratona": 42.195,
}


# =============================================================================
# Utilitários de formatação
# =============================================================================

def format_pace(seconds_per_km: float) -> str:
    """Converte segundos por km para formato min:sec/km."""
    seconds = max(0, int(round(seconds_per_km)))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}/km"


def min_km_to_ms(seconds_per_km: float) -> float:
    """Converte segundos por km para m/s."""
    return round(1000 / seconds_per_km, 3)


# =============================================================================
# Geração de zonas de treino
# =============================================================================

def gerar_zonas(vdot: float) -> dict:
    """
    Gera as 5 zonas de ritmo a partir do VDOT.

    - Easy: 59–74% do VDOT (faixa)
    - Marathon: derivado do ritmo equivalente de maratona
    - Threshold: 83–88% do VDOT (faixa)
    - Interval: 95–100% do VDOT (faixa)
    - Repetition: ~105% do VDOT
    """
    zonas = {}

    # Easy: 59-74% do VDOT
    e_slow = pace_for_fraction(vdot, 0.59)
    e_fast = pace_for_fraction(vdot, 0.74)
    zonas["easy"] = {
        "pace_range": f"{format_pace(e_slow)}-{format_pace(e_fast)}",
        "ms_min": min_km_to_ms(e_slow),
        "ms_max": min_km_to_ms(e_fast),
        "description": "Recuperação, base aeróbica, aquecimento/desaquecimento",
    }

    # Marathon: derivado do ritmo equivalente de maratona
    marathon_seconds = equivalent_time(vdot, RACE_DISTANCES_KM["Maratona"])
    m_pace = marathon_seconds / RACE_DISTANCES_KM["Maratona"]
    zonas["marathon"] = {
        "pace": format_pace(m_pace),
        "ms": min_km_to_ms(m_pace),
        "description": "Ritmo de maratona, longões",
    }

    # Threshold: 83-88% do VDOT
    t_fast = pace_for_fraction(vdot, 0.88)
    t_slow = pace_for_fraction(vdot, 0.83)
    zonas["threshold"] = {
        "pace_range": f"{format_pace(t_fast)}-{format_pace(t_slow)}",
        "ms_min": min_km_to_ms(t_slow),
        "ms_max": min_km_to_ms(t_fast),
        "description": "Limiar de lactato, tempo runs",
    }

    # Interval: 95-100% do VDOT
    i_fast = pace_for_fraction(vdot, 1.00)
    i_slow = pace_for_fraction(vdot, 0.95)
    zonas["interval"] = {
        "pace_range": f"{format_pace(i_slow)}-{format_pace(i_fast)}",
        "ms_min": min_km_to_ms(i_slow),
        "ms_max": min_km_to_ms(i_fast),
        "description": "VO2max, esforços de 2-4 min",
    }

    # Repetition: ~105% do VDOT
    r_pace = pace_for_fraction(vdot, 1.05)
    zonas["repetition"] = {
        "pace": format_pace(r_pace),
        "ms": min_km_to_ms(r_pace),
        "description": "Repetições curtas, 800m-1km",
    }

    return zonas


# =============================================================================
# Entrevista interativa
# =============================================================================

def entrevista_interativa() -> dict:
    """Roda a entrevita interativa com o corredor."""
    print("=" * 60)
    print("🏃 CALIBRAÇÃO DE ZONAS VDOT - GARMIN MCP")
    print("=" * 60)
    print()
    print("Vou calcular suas zonas de ritmo personalizadas baseadas")
    print("no resultado do seu último teste. Essas zonas serão usadas")
    print("nas skills de análise e criação de treinos.")
    print()

    # Perguntar distância
    print("Qual a distância do seu último teste?")
    for key, info in TEST_DISTANCES.items():
        print(f"  {key}. {info['name']}")

    while True:
        escolha = input("\nEscolha (1-7): ").strip()
        if escolha in TEST_DISTANCES:
            break
        print("❌ Opção inválida. Escolha entre 1 e 7.")

    distancia_info = TEST_DISTANCES[escolha]

    if distancia_info["meters"] is None:
        # Outra distância
        while True:
            try:
                dist_km = float(input("Qual a distância em km? (ex: 8.5): ").strip().replace(",", "."))
                if dist_km > 0:
                    distancia_metros = dist_km * 1000
                    break
                print("❌ Distância deve ser maior que 0.")
            except ValueError:
                print("❌ Valor inválido. Digite um número.")
    else:
        distancia_metros = distancia_info["meters"]

    # Perguntar tempo
    print()
    print("Qual foi o tempo total do teste?")
    print("Formato: HH:MM:SS (ex: 00:43:16)")

    while True:
        tempo_str = input("Tempo: ").strip()
        try:
            partes = tempo_str.split(":")
            if len(partes) == 3:
                horas = int(partes[0])
                minutos = int(partes[1])
                segundos = int(partes[2])
                total_seconds = horas * 3600 + minutos * 60 + segundos
                if total_seconds > 0:
                    break
                print("❌ Tempo deve ser maior que zero.")
            elif len(partes) == 2:
                minutos = int(partes[0])
                segundos = int(partes[1])
                total_seconds = minutos * 60 + segundos
                if total_seconds > 0:
                    break
                print("❌ Tempo deve ser maior que zero.")
            else:
                print("❌ Formato inválido. Use MM:SS ou HH:MM:SS.")
        except ValueError:
            print("❌ Valor inválido. Use números apenas.")

    # Perguntar data do teste
    print()
    print("Qual foi a data do teste? (AAAA-MM-DD) [Enter = hoje]")
    while True:
        data_str = input("Data: ").strip()
        if not data_str:
            test_date = date.today().isoformat()
            break
        try:
            parsed = date.fromisoformat(data_str)
            if parsed > date.today():
                print("❌ A data do teste não pode ser no futuro.")
                continue
            test_date = parsed.isoformat()
            break
        except ValueError:
            print("❌ Formato inválido. Use AAAA-MM-DD.")

    # Calcular VDOT
    vdot = round(calculate_vdot(distancia_metros, total_seconds), 1)

    # Gerar zonas
    zonas = gerar_zonas(vdot)

    # Calcular equivalências
    equivalencias = {}
    for label, dist_km in RACE_DISTANCES_KM.items():
        pred_seconds = equivalent_time(vdot, dist_km)
        equivalencias[label] = format_pace(pred_seconds / dist_km)

    # Mostrar resultado
    print()
    print("=" * 60)
    print(f"📊 VDOT CALCULADO: {vdot}")
    print("=" * 60)
    print()
    print("Tempos equivalentes estimados:")
    for label, pace in equivalencias.items():
        print(f"  {label:16s} {pace}")
    print()
    print("Suas zonas de ritmo personalizadas:")
    print()

    for nome, dados in zonas.items():
        if "pace_range" in dados:
            print(f"  {nome.upper():12} {dados['pace_range']:>20}  ({dados['description']})")
        else:
            print(f"  {nome.upper():12} {dados['pace']:>20}  ({dados['description']})")

    print()

    # Confirmar
    confirmacao = input("Salvar essas zonas? (s/n): ").strip().lower()
    if confirmacao != "s":
        print("❌ Cancelado. Nada foi salvo.")
        sys.exit(0)

    # Salvar
    config = {
        "vdot": vdot,
        "source": f"{distancia_info['name']} em {tempo_str}",
        "test_date": test_date,
        "distancia_metros": distancia_metros,
        "tempo_segundos": total_seconds,
        "zones": zonas,
        "equivalencias": equivalencias,
    }

    return config


# =============================================================================
# Gerenciamento de configuração
# =============================================================================

def verificar_config_existente() -> dict | None:
    """Verifica se já existe uma configuração salva."""
    config_path = Path(get_settings().vdot_zones_path)

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def salvar_config(config: dict) -> None:
    """Salva a configuração no arquivo JSON."""
    config_path = Path(get_settings().vdot_zones_path)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Configuração salva em: {config_path}")


def save_calibration_to_db(config: dict, user_id: int = DEFAULT_USER_ID) -> None:
    """Salva a calibração no banco de dados (upsert por user_id).

    Transação: commit no DB + escrita no JSON (JSON por último para
    compatibilidade com painéis legacy que ainda leem o arquivo).
    """
    with SessionLocal() as db:
        # Verificar se já existe linha para o usuário
        existing = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user_id).first()

        if existing:
            # Atualizar existente (upsert)
            existing.vdot = config["vdot"]
            existing.source = config["source"]
            existing.test_date = date.fromisoformat(config["test_date"])
            existing.distance_m = config["distancia_metros"]
            existing.time_s = config["tempo_segundos"]
            existing.zones = config["zones"]
            existing.equivalencias = config["equivalencias"]
            existing.valid_from = date.fromisoformat(config["test_date"])
        else:
            # Inserir nova
            new_config = VdotZoneConfig(
                user_id=user_id,
                vdot=config["vdot"],
                source=config["source"],
                test_date=date.fromisoformat(config["test_date"]),
                distance_m=config["distancia_metros"],
                time_s=config["tempo_segundos"],
                zones=config["zones"],
                equivalencias=config["equivalencias"],
                valid_from=date.fromisoformat(config["test_date"]),
            )
            db.add(new_config)

        db.commit()
        print(f"✅ Calibração salva no banco para user_id={user_id}")


def mostrar_config_existente(config: dict) -> None:
    """Mostra a configuração existente."""
    print("=" * 60)
    print("📋 CONFIGURAÇÃO EXISTENTE")
    print("=" * 60)
    print()
    print(f"  VDOT: {config['vdot']}")
    print(f"  Fonte: {config['source']}")
    print(f"  Data do teste: {config['test_date']}")
    print()
    print("Zonas atuais:")
    print()

    for nome, dados in config["zones"].items():
        if "pace_range" in dados:
            print(f"  {nome.upper():12} {dados['pace_range']:>20}")
        else:
            print(f"  {nome.upper():12} {dados['pace']:>20}")

    print()


# =============================================================================
# Main
# =============================================================================

def main():
    """Função principal."""
    # Verificar argumentos
    force = "--force" in sys.argv
    check_only = "--check" in sys.argv

    # Verificar se já existe
    config_existente = verificar_config_existente()

    if check_only:
        if config_existente:
            mostrar_config_existente(config_existente)
            sys.exit(0)
        else:
            print("❌ Nenhuma configuração encontrada.")
            print("Rode sem argumentos para fazer a entrevista.")
            sys.exit(1)

    if config_existente and not force:
        mostrar_config_existente(config_existente)
        print()

        atualizar = input("Deseja atualizar? (s/n): ").strip().lower()
        if atualizar != "s":
            print("✅ Mantendo configuração existente.")
            sys.exit(0)

    # Rodar entrevista
    config = entrevista_interativa()
    salvar_config(config)
    save_calibration_to_db(config)

    print()
    print("🎉 Calibração concluída!")
    print("As zonas de ritmo estão prontas para uso nas skills:")
    print("  - analyze-garmin-run")
    print("  - create-garmin-training")


if __name__ == "__main__":
    main()
