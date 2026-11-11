// 结构对比：忽略字符串 / 模板字面量内容，只比较 AST 形状。 node qa/ast_diff.mjs <old.js> <new.js>
import { createRequire } from 'node:module';
import fs from 'node:fs';
import { execSync } from 'node:child_process';
const require = createRequire('/tmp/tools/');
const acorn = require('acorn');
const strip = s => s.replace(/^<script[^>]*>/, '').replace(/<\/script>\s*$/, '');
function shape(file) {
  const ast = acorn.parse(strip(fs.readFileSync(file, 'utf8')), { ecmaVersion: 'latest', sourceType: 'script' });
  const out = [];
  (function walk(n, d) {
    if (!n || typeof n.type !== 'string') return;
    let tag = n.type;
    if (n.type === 'Identifier') tag += ':' + n.name;
    else if (n.type === 'Literal') tag += typeof n.value === 'string' ? ':str' : ':' + String(n.raw);
    else if (n.type === 'TemplateElement') tag += ':q';
    else if (n.operator) tag += ':' + n.operator;
    else if (n.kind) tag += ':' + n.kind;
    out.push(' '.repeat(Math.min(d, 40)) + tag);
    for (const k of Object.keys(n)) {
      if (k === 'type' || k === 'start' || k === 'end') continue;
      const v = n[k];
      if (Array.isArray(v)) v.forEach(c => walk(c, d + 1)); else if (v && typeof v.type === 'string') walk(v, d + 1);
    }
  })(ast, 0);
  return out;
}
const [a, b] = [shape(process.argv[2]), shape(process.argv[3])];
fs.writeFileSync('/tmp/ast_a.txt', a.join('\n') + '\n'); fs.writeFileSync('/tmp/ast_b.txt', b.join('\n') + '\n');
console.log(`nodes: ${a.length} -> ${b.length}`);
try { execSync('diff /tmp/ast_a.txt /tmp/ast_b.txt > /tmp/ast.diff'); console.log('AST shapes identical'); }
catch (e) { const d = fs.readFileSync('/tmp/ast.diff', 'utf8').split('\n'); console.log(`diff lines: ${d.length}`); console.log(d.slice(0, +(process.argv[4] || 60)).join('\n')); }
