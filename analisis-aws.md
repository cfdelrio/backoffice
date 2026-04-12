# Análisis AWS — prode-caballito

## Infraestructura

| Componente | Detalle |
|---|---|
| Lambda principal | `prode-api` — Node.js 20.x, Express.js |
| Base de datos | PostgreSQL RDS `prode-db.c850syqeokik.us-east-1.rds.amazonaws.com` |
| DB name / user | `prode` / `postgres` |
| IAM Role | `arn:aws:iam::358170204344:role/lambda-prode-role` |
| Credenciales AWS | `/home/user/.aws/credentials` (key: `AKIAVGZE3TC4MV3WXBVL`) |
| Proxy HTTPS | `*.amazonaws.com` permitido vía `HTTPS_PROXY` |

## Esquema de tablas relevantes

### `matches`
```
id uuid, home_team, away_team, start_time, time_cutoff,
halftime_minutes, estado (scheduled|live|halftime|finished|cancelled),
finished bool, resultado_local, resultado_visitante,
planilla_id uuid, tournament_id uuid, created_at, updated_at
```

### `bets`
```
id uuid, planilla_id uuid, match_id uuid,
goles_local int, goles_visitante int, created_at, updated_at
```

### `tournaments`
```
id uuid, name, description, fase, start_date, end_date,
status, is_active bool, cutoff_minutes int, created_at, updated_at
```

### `bet_view_access` (nueva — creada en sesión)
```
viewer_user_id uuid, target_user_id uuid, match_id uuid
PRIMARY KEY (viewer_user_id, target_user_id, match_id)
```

### `planillas`
```
id uuid, user_id uuid, nombre_planilla, precio_pagado bool, created_at
```

## Cambios deployados en esta sesión

### Backend `prode-api` Lambda
Nuevos endpoints en `routes/bets.js`:

```js
// GET /bets/my-unlocks
// Retorna las apuestas desbloqueadas por el usuario autenticado
router.get('/my-unlocks', authMiddleware, async (req, res) => {
  const result = await db.query(
    'SELECT target_user_id, match_id FROM bet_view_access WHERE viewer_user_id = $1',
    [req.user.userId]
  );
  res.json({ success: true, data: result.rows });
});

// POST /bets/unlock-view
// Desbloquea permanentemente la apuesta de otro jugador en un partido específico
router.post('/unlock-view', authMiddleware, async (req, res) => {
  const { target_user_id, match_id } = req.body;
  await db.query(`CREATE TABLE IF NOT EXISTS bet_view_access (
    viewer_user_id uuid, target_user_id uuid, match_id uuid,
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (viewer_user_id, target_user_id, match_id)
  )`);
  await db.query(
    `INSERT INTO bet_view_access (viewer_user_id, target_user_id, match_id)
     VALUES ($1, $2, $3) ON CONFLICT DO NOTHING`,
    [req.user.userId, target_user_id, match_id]
  );
  res.json({ success: true, message: 'Apuesta desbloqueada correctamente' });
});
```

## Datos de prueba — Mundial 2026

- **Tournament ID:** `dbd5881d-56f1-4275-b07e-aa7f44ba14e3`
- **72 partidos** (grupos A-L, fixture real del sorteo diciembre 2024)
- **3824 apuestas** inventadas para 59 planillas existentes

### Grupos del sorteo (diciembre 2024)
| Grupo | Equipo 1 | Equipo 2 | Equipo 3 | Equipo 4 |
|---|---|---|---|---|
| A | Mexico | South Korea | South Africa | Czech Republic |
| B | Canada | Switzerland | Qatar | Bosnia Herzegovina |
| C | Brazil | Morocco | Scotland | Haiti |
| D | USA | Turkey | Paraguay | Australia |
| E | Germany | Ivory Coast | Ecuador | Curacao |
| F | Netherlands | Japan | Sweden | Tunisia |
| G | Belgium | Egypt | Iran | New Zealand |
| H | Spain | Uruguay | Saudi Arabia | Cape Verde |
| I | France | Norway | Senegal | Iraq |
| J | Argentina | Austria | Algeria | Jordan |
| K | Portugal | Colombia | DR Congo | Uzbekistan |
| L | England | Croatia | Ghana | Panama |

## Lambda temporal `prode-sql-temp`
Creada para acceso directo a RDS durante esta sesión (pg8000 + psycopg2).
**Pendiente eliminar** cuando ya no sea necesaria.
