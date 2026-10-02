// Offline build only: no sockets, package installation, or upstream scripts.
// Pass the isolated cache prepared with the pinned official archive/dependencies.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import crypto from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const cache=path.resolve(process.argv[2]??'');
if (!process.argv[2] || cache.toLowerCase().startsWith(root.toLowerCase()+path.sep)) throw Error('Use isolated external cache');
const lock=JSON.parse(fs.readFileSync(path.join(root,'upstream-lock.json'),'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(hash(path.join(cache,'upstream.zip'))!==lock.archiveSha256)throw Error('Upstream archive mismatch');
const upstream=path.join(cache,'PixelStreamingInfrastructure-'+lock.commit);
for(const [p,h] of Object.entries(lock.sourceHashes))if(hash(path.join(upstream,p))!==h)throw Error('Upstream source mismatch');
if(hash(path.join(cache,'build-deps','package-lock.json'))!==lock.buildDependencyLockSha256)throw Error('Dependency lock mismatch');
const req=createRequire(path.join(cache,'build-deps','package.json'));
const esbuild=req('esbuild');
const result=await esbuild.build({entryPoints:[path.join(root,'browser','main.mjs')],bundle:true,format:'esm',
  platform:'browser',target:['es2022'],outfile:path.join(cache,'out','main.js'),metafile:true,
  nodePaths:[path.join(cache,'build-deps','node_modules')],
  alias:{'@epicgames-ps/lib-pixelstreamingfrontend-ue5.8':path.join(upstream,'Frontend/library/src/pixelstreamingfrontend.ts'),
    '@epicgames-ps/lib-pixelstreamingcommon-ue5.8':path.join(upstream,'Common/src/pixelstreamingcommon.ts')}});
fs.mkdirSync(path.join(cache,'out'),{recursive:true});
fs.copyFileSync(path.join(root,'browser/index.html'),path.join(cache,'out/index.html'));
fs.writeFileSync(path.join(cache,'out/build-result.json'),JSON.stringify({commit:lock.commit,
  sha256:hash(path.join(cache,'out/main.js')),inputCount:Object.keys(result.metafile.inputs).length},null,2));
console.log('Browser bundle built offline; no server/native execution.');
