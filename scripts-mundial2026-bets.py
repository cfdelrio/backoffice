#!/usr/bin/env python3
"""
Genera apuestas para Mundial 2026 con BATCH inserts (1 Lambda call por planilla).
"""
import boto3, json, os, random, uuid

os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/home/user/.aws/credentials'
lambda_client = boto3.client('lambda', region_name='us-east-1')

TOURNAMENT_ID = 'dbd5881d-56f1-4275-b07e-aa7f44ba14e3'

def sql(query):
    payload = {'sql': query, 'params': []}
    resp = lambda_client.invoke(FunctionName='prode-sql-temp', Payload=json.dumps(payload))
    raw = resp['Payload'].read()
    parsed = json.loads(raw)
    if isinstance(parsed, dict) and 'body' in parsed:
        return json.loads(parsed['body'])
    elif isinstance(parsed, dict) and 'errorMessage' in parsed:
        raise RuntimeError(f"Lambda error: {parsed['errorMessage']}\nSQL: {query[:300]}")
    raise RuntimeError(f"Unexpected: {str(parsed)[:300]}")

# ─────────────────────────────────────────────
# 1. Obtener matches del torneo
# ─────────────────────────────────────────────
print("Obteniendo matches del Mundial 2026...")
res = sql(f"SELECT id FROM matches WHERE tournament_id = '{TOURNAMENT_ID}' ORDER BY start_time")
match_ids = [r['id'] for r in res['rows']]
print(f"  {len(match_ids)} matches encontrados")

if not match_ids:
    print("ERROR: No hay matches. Correr mundial2026.py primero.")
    exit(1)

# ─────────────────────────────────────────────
# 2. Verificar apuestas ya existentes
# ─────────────────────────────────────────────
res = sql(f"""SELECT COUNT(*) as cnt FROM bets
WHERE match_id IN (SELECT id FROM matches WHERE tournament_id = '{TOURNAMENT_ID}')""")
existing_bets = res['rows'][0]['cnt']
print(f"  Apuestas existentes: {existing_bets}")

if existing_bets > 0:
    confirm = input(f"\nYa hay {existing_bets} apuestas. ¿Borrar y regenerar? (s/n): ").strip().lower()
    if confirm == 's':
        print("  Borrando apuestas existentes...")
        sql(f"""DELETE FROM bets
WHERE match_id IN (SELECT id FROM matches WHERE tournament_id = '{TOURNAMENT_ID}')""")
        print("  Listo.")
    else:
        print("Abortando.")
        exit(0)

# ─────────────────────────────────────────────
# 3. Obtener planillas
# ─────────────────────────────────────────────
res = sql("SELECT id FROM planillas ORDER BY created_at")
planillas = [r['id'] for r in res['rows']]
print(f"\n{len(planillas)} planillas a procesar")

# ─────────────────────────────────────────────
# 4. Distribución de scores realista
# ─────────────────────────────────────────────
SCORE_POOL = []
for h, a, w in [
    (0,0,8), (1,0,14), (0,1,14), (1,1,12),
    (2,0,10), (0,2,10), (2,1,9),  (1,2,9),
    (3,0,5),  (0,3,5),  (2,2,6),  (3,1,4),
    (1,3,4),  (3,2,2),  (2,3,2),  (4,0,1),
    (0,4,1),  (4,1,1),  (1,4,1),
]:
    SCORE_POOL.extend([(h, a)] * w)

# ─────────────────────────────────────────────
# 5. Insertar apuestas por planilla (BATCH)
# ─────────────────────────────────────────────
total_bets = 0
print("\nGenerando apuestas (batch por planilla)...")

for i, planilla_id in enumerate(planillas):
    values = []
    for match_id in match_ids:
        # ~90% de cobertura de apuestas
        if random.random() < 0.10:
            continue
        bet_id = str(uuid.uuid4())
        h, a = random.choice(SCORE_POOL)
        values.append(f"('{bet_id}', '{planilla_id}', '{match_id}', {h}, {a})")

    if not values:
        continue

    # Un solo INSERT con todos los values de esta planilla
    vals_sql = ',\n    '.join(values)
    query = f"""INSERT INTO bets (id, planilla_id, match_id, goles_local, goles_visitante)
VALUES
    {vals_sql}
ON CONFLICT DO NOTHING"""

    sql(query)
    total_bets += len(values)
    print(f"  [{i+1:2d}/{len(planillas)}] {planilla_id[:8]}... → {len(values)} apuestas")

print(f"\nTotal apuestas insertadas: {total_bets}")

# ─────────────────────────────────────────────
# 6. Verificación final
# ─────────────────────────────────────────────
res = sql(f"""SELECT COUNT(*) as cnt FROM bets
WHERE match_id IN (SELECT id FROM matches WHERE tournament_id = '{TOURNAMENT_ID}')""")
print(f"Apuestas en DB: {res['rows'][0]['cnt']}")
print("\n✓ Listo!")
