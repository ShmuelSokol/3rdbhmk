// Bundles the walkthrough into ../docs, the folder GitHub Pages can serve as-is.
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const out = path.resolve(root, '../docs');
fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(path.join(root, 'public'), out, { recursive: true });
fs.writeFileSync(path.join(out, '.nojekyll'), '');
const result = await build({
  entryPoints: [path.join(root, 'src/main.js')],
  bundle: true, format: 'esm', minify: true, target: ['es2020'],
  outfile: path.join(out, 'app.js'), legalComments: 'none', metafile: true,
  loader: { '.json': 'json' },
});
const bytes = Object.values(result.metafile.outputs)[0].bytes;
console.log(`docs/app.js ${(bytes / 1024).toFixed(0)} kB`);
