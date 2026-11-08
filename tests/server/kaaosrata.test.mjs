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

test('Kaaosrata v7 separates redesigned courses from v6 while preserving main and old lists', async () => {
  const env={DB:makeD1(),ADMIN_KEY:'test'}, player='d'.repeat(32);
  const call=async(method,path,body)=>{
    const response=await handle(new Request('https://pelit.test/api/'+path,{
      method,headers:{'content-type':'application/json'},...(body?{body:JSON.stringify(body)}:{})
    }),env);
    return {status:response.status,body:await response.json()};
  };
  await call('POST','players',{id:player,name:'Testi454v7'});
  const score={player,game:'kaaosrata',version:6,score:30};
  for(const board of ['hihna','laatat','finaali']) {
    assert.equal((await call('POST','scores',{...score,board})).status,200);
    assert.equal((await call('POST','scores',{...score,version:7,board:board+'7',score:60})).status,200);
    assert.equal((await call('POST','scores',{...score,version:7,board})).status,400);
    assert.equal((await call('POST','scores',{...score,board:board+'7'})).status,400);
    assert.equal((await call('GET','scores?game=kaaosrata&board='+board+'&player='+player)).body.mine.score,30);
    assert.equal((await call('GET','scores?game=kaaosrata&board='+board+'7&player='+player)).body.mine.score,60);
  }
  for(const version of [1,5,6,7]) {
    assert.equal((await call('POST','scores',{...score,board:'main',version})).status,200);
  }
});

test('Kaaosrata v8 keeps v7 lists apart from its harder courses', async () => {
  const env={DB:makeD1(),ADMIN_KEY:'test'}, player='e'.repeat(32);
  const call=async(method,path,body)=>{
    const response=await handle(new Request('https://pelit.test/api/'+path,{
      method,headers:{'content-type':'application/json'},...(body?{body:JSON.stringify(body)}:{})
    }),env);
    return {status:response.status,body:await response.json()};
  };
  await call('POST','players',{id:player,name:'Testi454v8'});
  const score={player,game:'kaaosrata',version:7,score:50};
  for(const board of ['hihna','laatat','finaali']) {
    assert.equal((await call('POST','scores',{...score,board:board+'7'})).status,200);
    assert.equal((await call('POST','scores',{...score,version:8,board:board+'8',score:70})).status,200);
    assert.equal((await call('POST','scores',{...score,version:8,board:board+'7'})).status,400);
    assert.equal((await call('POST','scores',{...score,board:board+'8'})).status,400);
    assert.equal((await call('GET','scores?game=kaaosrata&board='+board+'7&player='+player)).body.mine.score,50);
    assert.equal((await call('GET','scores?game=kaaosrata&board='+board+'8&player='+player)).body.mine.score,70);
  }
  assert.equal((await call('POST','scores',{...score,version:8,board:'main'})).status,200);
});
