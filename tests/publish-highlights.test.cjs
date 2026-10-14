const {test}=require('node:test'), assert=require('node:assert/strict');
const {canonical,verifyInventory}=require('../scripts/publish-highlights.cjs');
const book={asin:'B000000001',title:'Example',author:'Author',highlights:[{id:'a',text:'Text'}]};
test('ignore timestamps and object key order, detect same-count edits',()=>{
  const a={run:{timestamp:'old'},books:[book]};
  const b={run:{timestamp:'new'},books:[{author:'Author',title:'Example',asin:'B000000001',highlights:[{text:'Text',id:'a'}]}]};
  assert.equal(canonical(a),canonical(b));
  b.books[0].highlights[0].text='Edited';
  assert.notEqual(canonical(a),canonical(b));
});
test('reject empty or duplicate exports',()=>{
  assert.throws(()=>canonical({books:[]}));
  assert.throws(()=>canonical({books:[book,book]}));
});
test('reject unrelated file mutations or additions',()=>{
  const before=[{path:'/index.html',hash:'old'},{path:'/public/files/highlights.json',hash:'old'}];
  const good=[before[0],{...before[1],hash:'new'}];
  verifyInventory(before,good,'new');
  assert.throws(()=>verifyInventory(before,[{...before[0],hash:'oops'},good[1]],'new'));
  assert.throws(()=>verifyInventory(before,[...good,{path:'/oops',hash:'new'}],'new'));
});
