// Replace only the highlights file in the exact current Firebase Hosting release.
const fs = require('node:fs'), path = require('node:path');
const crypto = require('node:crypto'), zlib = require('node:zlib');
const { Readable } = require('node:stream');
const { isDeepStrictEqual } = require('node:util');
const SITE = 'shane-neeley', FILE = '/public/files/highlights.json';
const SITE_REPO = path.resolve(__dirname, '../../shanesite');

function canonical(data) {
  if (!Array.isArray(data.books) || !data.books.length) throw Error('Empty export');
  const seen = new Set();
  const books = data.books.map(book => {
    if (!/^[A-Z0-9]{10}$/.test(book.asin) || seen.has(book.asin) || !book.title ||
        !book.author || !Array.isArray(book.highlights)) throw Error('Invalid book');
    seen.add(book.asin);
    const ids = new Set();
    for (const h of book.highlights) {
      if (!h.id || !h.text || ids.has(h.id)) throw Error('Invalid highlight');
      ids.add(h.id);
    }
    return { ...book, highlights: [...book.highlights].sort((a,b)=>a.id.localeCompare(b.id)) };
  }).sort((a,b)=>a.asin.localeCompare(b.asin));
  const stable = v => Array.isArray(v) ? v.map(stable) : v && typeof v === 'object' ?
    Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])])) : v;
  return JSON.stringify(stable(books));
}

function verifyInventory(before, after, replacementHash) {
  const map = new Map(after.map(f=>[f.path, f.hash]));
  if (map.size !== after.length || before.length !== after.length) throw Error('File count changed');
  for (const f of before) {
    if (map.get(f.path) !== (f.path === FILE ? replacementHash : f.hash))
      throw Error('Unexpected asset change: '+f.path);
  }
  if (!map.has(FILE)) throw Error('Highlights path missing');
}

async function main() {
  const source = path.resolve(process.argv[2] || 'data/highlights.json');
  const bytes = fs.readFileSync(source), candidate = JSON.parse(bytes);
  const liveResponse = await fetch('https://www.shaneneeley.com'+FILE+'?refresh='+Date.now(),
    {signal:AbortSignal.timeout(30000)});
  if (!liveResponse.ok) throw Error('Live highlights HTTP '+liveResponse.status);
  const live = await liveResponse.json();
  if (canonical(candidate) === canonical(live)) {
    console.log(JSON.stringify({changed:false,published:false})); return;
  }
  if (!live.books.every(b=>candidate.books.some(c=>c.asin===b.asin)))
    throw Error('Candidate drops existing books');
  if (!process.argv.includes('--publish')) {
    console.log(JSON.stringify({changed:true,published:false,books:candidate.books.length,
      highlights:candidate.books.reduce((n,b)=>n+b.highlights.length,0)})); return;
  }
  const base = path.join(SITE_REPO, 'node_modules/firebase-tools/lib');
  const auth = require(path.join(base,'auth')), api = require(path.join(base,'apiv2'));
  const account = auth.getGlobalDefaultAccount();
  if (!account?.tokens?.refresh_token) throw Error('Firebase saved login unavailable');
  api.setRefreshToken(account.tokens.refresh_token);
  const client = new api.Client({urlPrefix:'https://firebasehosting.googleapis.com',apiVersion:'v1beta1'});
  const latest = async () => (await client.get(`/sites/${SITE}/releases`,
    {queryParams:{pageSize:1}})).body.releases[0];
  const previous = await latest();
  const inventory = async version => {
    const files=[]; let token;
    do {
      const res=(await client.get('/'+version+'/files',
        {queryParams:{pageSize:1000,...(token?{pageToken:token}:{})}})).body;
      files.push(...(res.files||[])); token=res.nextPageToken;
    } while(token);
    return files;
  };
  const oldFiles = await inventory(previous.version.name);
  if (!oldFiles.some(f=>f.path===FILE)) throw Error('Live highlights missing');
  const backupDir=path.resolve(__dirname,'../data/backups');
  fs.mkdirSync(backupDir,{recursive:true,mode:0o700});
  fs.writeFileSync(path.join(backupDir,previous.version.name.split('/').pop()+'.json'),
    JSON.stringify({release:previous,files:oldFiles,highlights:live},null,2),{mode:0o600});
  const operation=(await client.post(`/sites/${SITE}/versions:clone`,{
    sourceVersion:previous.version.name,finalize:false,
    exclude:{regexes:['^/public/files/highlights\\.json$']}
  })).body;
  let completed;
  for(let n=0;n<30;n++) {
    completed=(await client.get('/'+operation.name)).body;
    if(completed.done) break;
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  if(!completed?.done || completed.error) throw Error('Hosting clone failed');
  const version=completed.response.name;
  const zip=zlib.gzipSync(bytes,{level:9});
  const hash=crypto.createHash('sha256').update(zip).digest('hex');
  const population=(await client.post('/'+version+':populateFiles',{files:{[FILE]:hash}})).body;
  const uploader=new api.Client({urlPrefix:population.uploadUrl,auth:true});
  for(const needed of population.uploadRequiredHashes||[]) {
    if(needed!==hash) throw Error('Unexpected upload hash');
    const res=await uploader.request({method:'POST',path:'/'+hash,body:Readable.from(zip),
      responseType:'stream',resolveOnHTTPError:true});
    if(res.status>=400) throw Error('Upload failed HTTP '+res.status);
  }
  verifyInventory(oldFiles,await inventory(version),hash);
  const detail=(await client.get('/'+version)).body;
  if(!isDeepStrictEqual(detail.config,previous.version.config)) throw Error('Hosting config changed');
  await client.patch('/'+version,{status:'FINALIZED'},{queryParams:{updateMask:'status'}});
  if((await latest()).version.name!==previous.version.name) throw Error('Production changed; release aborted');
  const release=(await client.post(`/sites/${SITE}/releases`,
    {message:'Weekly Kindle highlights refresh only'}, {queryParams:{versionName:version}})).body;
  const report={changed:true,published:true,baseline:previous.version.name,version,
    release:release.name,unchanged_assets:oldFiles.length-1};
  fs.writeFileSync(path.resolve(__dirname,'../data/deployment.json'),JSON.stringify(report,null,2),{mode:0o600});
  const verify=await fetch('https://www.shaneneeley.com'+FILE+'?verified='+Date.now(),
    {signal:AbortSignal.timeout(30000)});
  if(!verify.ok || canonical(await verify.json())!==canonical(candidate))
    throw Error('Released but public verification failed; inspect data/deployment.json');
  fs.copyFileSync(source,path.join(SITE_REPO,'public/files/highlights.json'));
  console.log(JSON.stringify({...report,verified:true}));
}

module.exports={canonical,verifyInventory};
if(require.main===module) main().catch(e=>{console.error(e.message);process.exitCode=1;});
