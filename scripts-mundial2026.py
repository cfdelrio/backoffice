#!/usr/bin/env python3
"""
Inserta fixture completo del Mundial 2026 + apuestas inventadas para todos los planillas.
"""
import boto3, json, os, random, uuid
from datetime import datetime, timedelta, timezone

os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/home/user/.aws/credentials'
lambda_client = boto3.client('lambda', region_name='us-east-1')

TOURNAMENT_ID = 'dbd5881d-56f1-4275-b07e-aa7f44ba14e3'

def sql(query):
    """Ejecuta SQL via Lambda proxy. No params — usamos string formatting seguro."""
    payload = {'sql': query, 'params': []}
    resp = lambda_client.invoke(FunctionName='prode-sql-temp', Payload=json.dumps(payload))
    raw = resp['Payload'].read()
    parsed = json.loads(raw)
    if isinstance(parsed, dict) and 'body' in parsed:
        body = json.loads(parsed['body'])
        return body
    elif isinstance(parsed, dict) and 'errorMessage' in parsed:
        raise RuntimeError(f"Lambda error: {parsed['errorMessage']}\nSQL was: {query[:200]}")
    raise RuntimeError(f"Unexpected response: {str(parsed)[:300]}")

def q(s):
    """Escapa un string para SQL: duplica comillas simples."""
    return s.replace("'", "''")

def fmt_ts(dt):
    """Formatea datetime como string ISO para PostgreSQL."""
    return dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')

# ─────────────────────────────────────────────
# 1. Verificar tournament
# ─────────────────────────────────────────────
print("=" * 60)
print("Verificando tournament...")
res = sql(f"SELECT id, name FROM tournaments WHERE id = '{TOURNAMENT_ID}'")
if not res['rows']:
    raise RuntimeError("Tournament no encontrado! Verificar ID.")
print(f"  OK: {res['rows'][0]['name']}")

# ─────────────────────────────────────────────
# 2. Limpiar matches existentes del torneo
# ─────────────────────────────────────────────
existing = sql(f"SELECT COUNT(*) as cnt FROM matches WHERE tournament_id = '{TOURNAMENT_ID}'")
count = existing['rows'][0]['cnt']
print(f"\nMatches existentes: {count}")
if count > 0:
    print("  Limpiando bets y matches existentes...")
    # Primero borrar bets de esos matches
    sql(f"""DELETE FROM bets WHERE match_id IN (
        SELECT id FROM matches WHERE tournament_id = '{TOURNAMENT_ID}'
    )""")
    sql(f"DELETE FROM matches WHERE tournament_id = '{TOURNAMENT_ID}'")
    print("  Limpieza completada.")

# ─────────────────────────────────────────────
# 3. Fixture Mundial 2026 — 12 grupos, 4 equipos
# ─────────────────────────────────────────────
GROUPS = {
    'A': ['Mexico',          'South Korea',   'South Africa',  'Czech Republic'],
    'B': ['Canada',          'Switzerland',   'Qatar',         'Bosnia Herzegovina'],
    'C': ['Brazil',          'Morocco',       'Scotland',      'Haiti'],
    'D': ['USA',             'Turkey',        'Paraguay',      'Australia'],
    'E': ['Germany',         'Ivory Coast',   'Ecuador',       'Curacao'],
    'F': ['Netherlands',     'Japan',         'Sweden',        'Tunisia'],
    'G': ['Belgium',         'Egypt',         'Iran',          'New Zealand'],
    'H': ['Spain',           'Uruguay',       'Saudi Arabia',  'Cape Verde'],
    'I': ['France',          'Norway',        'Senegal',       'Iraq'],
    'J': ['Argentina',       'Austria',       'Algeria',       'Jordan'],
    'K': ['Portugal',        'Colombia',      'DR Congo',      'Uzbekistan'],
    'L': ['England',         'Croatia',       'Ghana',         'Panama'],
}

# Horarios base (UTC) por jornada:
# Jornada 1: 11-14 Junio 2026
# Jornada 2: 18-22 Junio 2026
# Jornada 3: 25-26 Junio 2026

BASE_J1 = datetime(2026, 6, 11, 17, 0, tzinfo=timezone.utc)
BASE_J2 = datetime(2026, 6, 18, 17, 0, tzinfo=timezone.utc)
BASE_J3 = datetime(2026, 6, 25, 20, 0, tzinfo=timezone.utc)

def group_times(group_idx):
    """Retorna los 3 horarios base de un grupo (una fecha por jornada)."""
    # Distribuimos grupos en días disponibles
    # J1: 11,12,13,14 -> 12 grupos en 4 días -> 3 grupos por día
    day_offset_j1 = group_idx // 3
    hour_offset_j1 = (group_idx % 3) * 4  # 17:00, 21:00 y al dia siguiente 01:00... simplificamos

    day_offset_j2 = group_idx // 3
    day_offset_j3 = group_idx // 6

    t1 = BASE_J1 + timedelta(days=day_offset_j1, hours=(group_idx % 3) * 3)
    t2 = BASE_J2 + timedelta(days=day_offset_j2, hours=(group_idx % 3) * 3)
    t3 = BASE_J3 + timedelta(days=day_offset_j3, hours=(group_idx % 6) * 1)
    return t1, t2, t3

# Rondos de cada grupo: (idx_local, idx_visitante)
ROUND_ROBIN = [
    (0, 1), (2, 3),  # Jornada 1
    (0, 2), (1, 3),  # Jornada 2
    (0, 3), (1, 2),  # Jornada 3
]

# Insertar matches
print("\n" + "=" * 60)
print("Insertando matches...")

match_ids = {}  # (group, local_idx, visit_idx) -> match_id

group_list = list(GROUPS.items())
for g_idx, (group, teams) in enumerate(group_list):
    t1, t2, t3 = group_times(g_idx)
    times = [t1, t1 + timedelta(hours=3), t2, t2 + timedelta(hours=3), t3, t3 + timedelta(hours=2)]

    for m_idx, (li, vi) in enumerate(ROUND_ROBIN):
        home = teams[li]
        away = teams[vi]
        match_id = str(uuid.uuid4())
        start_time = times[m_idx]
        cutoff = start_time - timedelta(minutes=15)

        key = (group, li, vi)
        match_ids[key] = {
            'id': match_id,
            'home': home,
            'away': away,
            'start_time': start_time,
        }

        qry = f"""INSERT INTO matches (
            id, home_team, away_team, start_time, time_cutoff,
            halftime_minutes, estado, finished,
            tournament_id
        ) VALUES (
            '{match_id}',
            '{q(home)}',
            '{q(away)}',
            '{fmt_ts(start_time)}',
            '{fmt_ts(cutoff)}',
            45,
            'scheduled',
            false,
            '{TOURNAMENT_ID}'
        )"""
        sql(qry)

    print(f"  Grupo {group}: {len(ROUND_ROBIN)} matches insertados")

total_matches = len(GROUPS) * 6
print(f"\nTotal matches insertados: {total_matches}")

# ─────────────────────────────────────────────
# 4. Obtener planillas
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("Obteniendo planillas...")
res = sql("SELECT id, user_id FROM planillas ORDER BY created_at")
planillas = res['rows']
print(f"  Total planillas: {len(planillas)}")

# ─────────────────────────────────────────────
# 5. Generar apuestas aleatorias
# ─────────────────────────────────────────────
# Distribución realista de goles en fútbol
SCORE_WEIGHTS = [
    (0, 0, 8), (1, 0, 14), (0, 1, 14), (1, 1, 12),
    (2, 0, 10), (0, 2, 10), (2, 1, 9),  (1, 2, 9),
    (3, 0, 5),  (0, 3, 5),  (2, 2, 6),  (3, 1, 4),
    (1, 3, 4),  (3, 2, 2),  (2, 3, 2),  (4, 0, 1),
    (0, 4, 1),  (4, 1, 1),  (1, 4, 1),
]
scores = [(h, a) for h, a, w in SCORE_WEIGHTS for _ in range(w)]

def random_score():
    return random.choice(scores)

all_matches = list(match_ids.values())
print(f"\nGenerando apuestas para {len(planillas)} planillas × {len(all_matches)} partidos...")

total_bets = 0
for p_idx, planilla in enumerate(planillas):
    planilla_id = planilla['id']

    for match in all_matches:
        # No todos los jugadores apuestan todos los partidos (~90% coverage)
        if random.random() < 0.10:
            continue

        bet_id = str(uuid.uuid4())
        home_goals, away_goals = random_score()

        qry = f"""INSERT INTO bets (
            id, planilla_id, match_id, goles_local, goles_visitante
        ) VALUES (
            '{bet_id}',
            '{planilla_id}',
            '{match['id']}',
            {home_goals},
            {away_goals}
        ) ON CONFLICT DO NOTHING"""
        sql(qry)
        total_bets += 1

    if (p_idx + 1) % 10 == 0 or p_idx == len(planillas) - 1:
        print(f"  Planilla {p_idx+1}/{len(planillas)}: {planilla_id[:8]}...")

print(f"\nTotal apuestas insertadas: {total_bets}")

# ─────────────────────────────────────────────
# 6. Verificación final
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("Verificación final:")
res = sql(f"SELECT COUNT(*) as cnt FROM matches WHERE tournament_id = '{TOURNAMENT_ID}'")
print(f"  Matches en DB: {res['rows'][0]['cnt']}")
res = sql(f"""SELECT COUNT(*) as cnt FROM bets
    WHERE match_id IN (SELECT id FROM matches WHERE tournament_id = '{TOURNAMENT_ID}')""")
print(f"  Apuestas en DB: {res['rows'][0]['cnt']}")

print("\n✓ Fixture Mundial 2026 cargado exitosamente!")
