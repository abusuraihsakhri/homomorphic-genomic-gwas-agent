'use strict';
// Dependency-free DOM smoke test for the static browser controller.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const elements = new Map();
function element() {
  return {
    value: '', hidden: false, textContent: '', children: [], listeners: {},
    addEventListener(event, listener) { this.listeners[event] = listener; },
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    remove() {}, click() {}
  };
}
function getElementById(id) {
  if (!elements.has(id)) elements.set(id, element());
  return elements.get(id);
}
const document = {
  getElementById, createElement() { return element(); },
  body: {append() {}}
};
let downloadBlob = null;
const URL = {
  createObjectURL(blob) { downloadBlob = blob; return 'blob:test'; },
  revokeObjectURL() {}
};
const context = {document, URL, Blob, setTimeout() {}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'app.js'), 'utf8'), context);
const trigger = (id, event) => getElementById(id).listeners[event]({preventDefault(){}});

(async () => {
  const inputs = ['case-alt', 'case-ref', 'control-alt', 'control-ref'];
  function setCounts(values) {inputs.forEach((id,i)=>getElementById(id).value=String(values[i]));}
  setCounts([30,70,15,85]);
  trigger('single-form', 'submit');
  assert.equal(getElementById('chi-stat').textContent,'6.4516');
  assert.equal(getElementById('p-stat').textContent,'0.011085');
  assert.equal(getElementById('odds-stat').textContent,'2.4286');
  setCounts([25,75,50,150]); trigger('single-form','submit');
  assert.equal(getElementById('p-stat').textContent,'1.0000');
  setCounts([-1,75,50,150]); trigger('single-form','submit');
  assert.equal(getElementById('result').hidden,true);
  assert.match(getElementById('single-error').textContent,/non-negative/);
  getElementById('reset-form').listeners.click();
  assert.equal(getElementById('case-alt').value,30);

  getElementById('csv-file').files=[{size:120, text: async() =>
    'variant_id,case_alt,case_ref,control_alt,control_ref\nrsExample,30,70,15,85\n=CMD,25,75,50,150\nbad,-1,5,2,8\n'}];
  await trigger('csv-file','change');
  assert.match(getElementById('batch-status').textContent,/2 variants analyzed; 1 invalid row/);
  assert.equal(getElementById('results-body').children.length,2);
  trigger('export-results','click');
  assert.match(await downloadBlob.text(),/"'=CMD"/);
  console.log('Browser controller smoke tests passed.');
})().catch(err => {console.error(err);process.exitCode=1;});
