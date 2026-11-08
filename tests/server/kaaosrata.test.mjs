import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../../server/api.js';
import { makeD1 } from './d1.mjs';

test('Kaaosrata keeps old main scores and separate times for all four courses', async () => {
  const env={DB:makeD1(),ADMIN_KEY:'test'}, player='c'.repeat(32);
  const call=async(method,path,body)=>{
    const response=await handle(new Request('https://pelit.test/api/'+path,{
      method,headers:{'content-type':'application/json'},...(body?{body:JSON.stringify(body)}:{})
    }),env);
    return {status:response.status,body:await response.json()};
  };
  await call('POST','players',{id:player,name:'Testi454'});
  const score={player,game:'kaaosrata',version:5,board:'main',score:61.2};
  assert.equal((await call('POST','scores',score)).status,200);
  for(const [i,board] of ['hihna','laatat','finaali'].entries()) {
    assert.equal((await call('POST','scores',{...score,version:6,board,score:40+i})).status,200);
    assert.equal((await call('GET','scores?game=kaaosrata&board='+board+'&player='+player)).body.mine.score,40+i);
  }
  assert.equal((await call('GET','scores?game=kaaosrata&board=main&player='+player)).body.mine.score,61.2);
  assert.equal((await call('POST','scores',{...score,version:6,board:'other'})).status,400);
  assert.equal((await call('GET','scores?game=kaaosrata&board=other')).status,400);
  env.DB.raw.prepare("UPDATE players SET status='approved' WHERE id=?").run(player);
  assert.equal((await call('GET','scores/top')).body.games.kaaosrata.board,'main');
});
