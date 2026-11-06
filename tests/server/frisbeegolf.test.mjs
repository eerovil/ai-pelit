import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

function setup() {
  const env = { DB: makeD1(), ADMIN_KEY: 'test' };
  const call = async (method, path, body) => {
    const result = await handle(new Request('https://pelit.test/api/' + path, {
      method, headers: { 'content-type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {}),
    }), env);
    return { status: result.status, body: await result.json() };
  };
  return { env, call };
}

test('Frisbeegolf keeps the lowest harder-rules score and excludes old versions', async () => {
  const { env, call } = setup(), player = 'f'.repeat(32);
  await call('POST', 'players', { id: player, name: 'Testi338' });
  const score = { player, game: 'frisbeegolf', board: 'v3', version: 3 };
  for (const n of [5, 0, -2, 1]) assert.equal((await call('POST', 'scores', { ...score, score: n })).status, 200);
  for (const version of [1, 2]) {
    for (const board of ['main', 'v3']) {
      assert.equal((await call('POST', 'scores', { ...score, version, board, score: -30 })).status, 400);
    }
  }
  env.DB.raw.prepare("UPDATE players SET status='approved' WHERE id=?").run(player);
  const list = await call('GET', 'scores?game=frisbeegolf&board=v3&player=' + player);
  assert.equal(list.body.mine.score, -2);
  assert.equal(list.body.rows[0].version, 3);
  assert.equal((await call('GET', 'scores/top')).body.games.frisbeegolf.board, 'v3');
  assert.equal((await call('GET', 'scores?game=frisbeegolf&board=main')).status, 400);
  assert.equal((await call('POST', 'scores', { ...score, board: 'other', score: -3 })).status, 400);
  assert.equal((await call('POST', 'scores', { ...score, version: 4, score: -3 })).status, 200);
});

test('Frisbeegolf cleanup deletes only v1/v2 rows and is safe to repeat', () => {
  const { env } = setup();
  const rows = [['frisbeegolf','main',1],['frisbeegolf','main',2],['frisbeegolf','v3',3],['frisbeegolf','v3',4],['minigolf','main',1]];
  rows.forEach(([game,board,version], i) => {
    const id = String(i).repeat(32);
    env.DB.raw.prepare("INSERT INTO players (id,name,created_at,updated_at) VALUES (?,?,?,?)").run(id,'Testi'+i,'2026-11-06','2026-11-06');
    env.DB.raw.prepare('INSERT INTO scores (game,board,player,score,version,at) VALUES (?,?,?,?,?,?)').run(game,board,id,-12,version,'2026-11-06');
  });
  const sql = readFileSync(new URL('../../migrations/0011_frisbeegolf_v3_scores.sql', import.meta.url), 'utf8');
  env.DB.raw.exec(sql);
  env.DB.raw.exec(sql);
  assert.deepEqual(env.DB.raw.prepare('SELECT game,version FROM scores ORDER BY game,version').all().map(r=>[r.game,r.version]), [['frisbeegolf',3],['frisbeegolf',4],['minigolf',1]]);
  assert.equal(env.DB.raw.prepare('SELECT COUNT(*) n FROM players').get().n, 5);
});
