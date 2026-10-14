// Helpers to paste into cua_repl after binding the signed-in notebook tab.
// Browser interactions must remain in cua_repl. No cookies/passwords are read.
let readLibrary = async (tab) => tab.playwright.evaluate(() =>
  Array.from(document.querySelectorAll('.kp-notebook-library-each-book')).map(e => ({
    asin: e.id, title: e.querySelector('h2').textContent,
    author: e.querySelector('p').textContent.replace(/^By:\s*/, ''),
    cover_url: e.querySelector('img').src,
  })));

let readBook = async (tab) => tab.playwright.evaluate(() => {
  const root = document.querySelector('#annotation-scroller');
  const meta = root.querySelector('#kp-notebook-annotation-count').textContent;
  return {
    title: root.querySelector('h3').textContent,
    asin: root.querySelector('a.kp-notebook-printable').href.split('/dp/')[1].split('?')[0],
    expected: Number(meta.match(/([\d,]+)\s*Highlights?/i)[1].replaceAll(',', '')),
    highlights: Array.from(root.querySelectorAll('.kp-notebook-highlight')).map(e => {
      const row = e.parentElement.parentElement.parentElement;
      const header = row.querySelector('#annotationHighlightHeader')?.textContent || '';
      const h = { id: e.id, text: e.querySelector('.a-size-base-plus').textContent,
        color: e.className.match(/kp-notebook-highlight-(yellow|blue|pink|orange)/)?.[1] || 'yellow' };
      for (const key of ['page', 'location']) {
        const m = header.match(new RegExp(key + ':?\\s*([\\d,]+)', 'i'));
        if (m) h[key] = Number(m[1].replaceAll(',', ''));
      }
      const note = row.querySelector('.kp-notebook-note .a-size-base-plus')?.textContent;
      if (note) h.note = note;
      return h;
    }),
  };
});

let captureBook = async (tab, info, capture) => {
  if (!/^[A-Z0-9]{10}$/.test(info.asin)) throw Error('Invalid ASIN');
  await tab.playwright.locator(`#kp-notebook-library #${info.asin} a`).click();
  await tab.playwright.locator('#annotation-scroller h3').filter({hasText:info.title})
    .waitFor({state:'visible',timeoutMs:10000});
  const result = await readBook(tab);
  if (result.asin !== info.asin || result.title !== info.title ||
      result.highlights.length !== result.expected)
    throw Error(`Incomplete or mismatched export: ${info.asin}`);
  capture.books = capture.books.filter(b => b.asin !== info.asin);
  capture.books.push({...info,highlights:result.highlights});
  capture.counts[info.asin] = result.expected;
  return {asin:info.asin,highlights:result.highlights.length};
};

let checkpoint = async (editor, capture) => {
  await editor.pressKey('super+a');
  await editor.paste(JSON.stringify(capture,null,2),{format:'text'});
  await editor.pressKey('super+s');
  // Avoid dumping the document/highlight text to the chat.
  return (await editor.getAXState({emit:false})).slice(0,150);
};
