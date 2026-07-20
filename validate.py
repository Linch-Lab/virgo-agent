"""Pre-commit validation for Virgo Agent app/index.html.
Run before every git push. Catches brace imbalance, duplicate functions, missing window exports.
"""
import re, sys

with open('app/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

errors = []
start = html.find('<script type="module">')
end = html.find('</script>', start)
if start == -1 or end == -1:
    print('ERROR: Cannot find module script')
    sys.exit(1)

js = html[start:end].replace('<script type="module">', '')
lines = js.split('\n')

# 1. Brace balance
depth = 1
for line in lines:
    depth += line.count('{') - line.count('}')
if depth != 1:
    errors.append(f'Brace imbalance: depth={depth}, diff={depth-1}')

# 2. Duplicate function declarations
funcs = {}
for i, line in enumerate(lines, 1):
    m = re.match(r'(?:async )?function (\w+)\(', line)
    if m:
        name = m.group(1)
        if name in funcs:
            errors.append(f'DUPLICATE function "{name}": line {i} and line {funcs[name]}')
        else:
            funcs[name] = i

# 3. Missing window exports for onclick handlers
onclick_fns = set(re.findall(r'onclick="(\w+)\(', html))
window_exports = set(re.findall(r'window\.(\w+)\s*=', js))
missing = onclick_fns - window_exports
if missing:
    errors.append(f'Missing window exports for onclick: {missing}')

if errors:
    print('❌ PRE-COMMIT CHECKS FAILED:')
    for e in errors:
        print(f'  {e}')
    sys.exit(1)
else:
    print(f'✅ PASSED: {len(funcs)} functions, braces OK, exports OK')
