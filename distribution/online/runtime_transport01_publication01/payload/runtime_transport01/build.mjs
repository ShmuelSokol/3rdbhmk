// Offline pinned source build; never installs or runs upstream bootstrap scripts.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [cacheArg,outArg]=process.argv.slice(2);
if(!cacheArg||!outArg)throw Error('Pass isolated cache and fresh output');
const cache=path.resolve(cacheArg),out=path.resolve(outArg);
if(fs.existsSync(out))throw Error('Fresh output required');
const lock=JSON.parse(fs.readFileSync(path.join(root,'upstream-lock.json'),'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(hash(path.join(cache,'upstream.zip'))!==lock.archiveSha256)throw Error('Archive mismatch');
const source=path.join(cache,'PixelStreamingInfrastructure-'+lock.commit);
for(const [name,h] of Object.entries(lock.sourceHashes))if(hash(path.join(source,name))!==h)throw Error('Official source mismatch');
if(hash(path.join(cache,'build-deps/package-lock.json'))!==lock.buildDependencyLockSha256)throw Error('Dependency lock mismatch');
const req=createRequire(path.join(cache,'build-deps/package.json'));
const result=await req('esbuild').build({entryPoints:[path.join(root,'runtime_transport01/entry.mjs')],
 bundle:true,format:'esm',platform:'browser',target:['es2022'],outfile:path.join(out,'app.js'),metafile:true,
 nodePaths:[path.join(cache,'build-deps/node_modules')],
 alias:{'@epicgames-ps/lib-pixelstreamingfrontend-ue5.8':path.join(source,'Frontend/library/src/pixelstreamingfrontend.ts'),
 '@epicgames-ps/lib-pixelstreamingcommon-ue5.8':path.join(source,'Common/src/pixelstreamingcommon.ts')}});
for(const n of ['index.html','style.css'])fs.copyFileSync(path.join(root,'runtime_transport01',n),path.join(out,n));
const files=Object.fromEntries(['app.js','index.html','style.css'].map(n=>[n,hash(path.join(out,n))]));
fs.writeFileSync(path.join(out,'assets.json'),JSON.stringify({schema:1,commit:lock.commit,files,inputCount:Object.keys(result.metafile.inputs).length},null,2)+'\n');
console.log(JSON.stringify({built:true,commit:lock.commit,files,inputCount:Object.keys(result.metafile.inputs).length}));
