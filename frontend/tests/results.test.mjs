import assert from 'node:assert/strict';
import { test, after } from 'node:test';
import React from 'react';
import { createServer as createHttpServer } from 'node:http';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({ server: { middlewareMode: true, hmr: { server: createHttpServer() } }, appType: 'custom' });
after(() => server.close());
const { ResultCard } = await server.ssrLoadModule('/src/main.tsx');
const fixture = { id:'fixture', label:'A', model:'Qwen test', created:0, duration:5.16,
  settings:{mode:'generate',target_text:'較長的新台詞'}, rating:null, asr_text:'較長的新台詞' };
function render(mode, duration) {
  return renderToStaticMarkup(React.createElement(ResultCard, {
    item:{...fixture,settings:{...fixture.settings,mode},replacement_duration:duration,shift_seconds:0},
    onSaved:()=>{},onError:()=>{}
  }));
}
for (const duration of [null, undefined, 2]) {
  test(`voice generation renders without replacement downloads: ${duration}`,()=>{
    const html=render('generate',duration);
    assert.match(html,/純人聲 WAV/);
    assert.doesNotMatch(html,/只下載替換片段|完整修正版 WAV/);
  });
}
test('replacement renders the selected segment and complete download',()=>{
  const html=render('replace',2);
  assert.match(html,/只下載替換片段（2.00 秒）/);
  assert.match(html,/完整修正版 WAV/);
});
for (const duration of [null,undefined]) {
  test(`legacy replacement without segment metadata renders: ${duration}`,()=>{
    const html=render('replace',duration);
    assert.doesNotMatch(html,/只下載替換片段/);
    assert.match(html,/完整修正版 WAV/);
  });
}
