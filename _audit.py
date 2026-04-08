import re, os

audit_files = [
    'game/entities/hero/__init__.py','game/entities/hero/actions.py','game/entities/hero/finders.py',
    'game/entities/hero/schedule.py','game/entities/hero/movement.py',
    'game/entities/bandit/__init__.py','game/entities/bandit/actions.py','game/entities/bandit/finders.py',
    'game/entities/bandit/schedule.py','game/entities/bandit/movement.py',
    'game/entities/dragon/__init__.py','game/entities/dragon/actions.py','game/entities/dragon/finders.py',
    'game/entities/dragon/schedule.py','game/entities/dragon/movement.py','game/entities/dragon/domain.py',
    'game/entities/settlement/settlement.py','game/entities/settlement/actions.py',
    'game/entities/settlement/finders.py','game/entities/settlement/schedule.py',
    'game/entities/settlement/expansion.py','game/entities/settlement/camp.py',
    'game/entities/settlement/village.py','game/entities/settlement/city.py',
    'game/entities/settlement/spire.py','game/entities/settlement/extractor.py',
    'game/entities/settlement/ruins.py',
    'game/entities/caravan.py','game/entities/cattle.py','game/entities/blessing.py',
    'game/entities/spirit.py',
    'game/entities/base/entity.py','game/entities/base/mobile.py','game/entities/base/scheduled.py',
    'game/entities/base/engaging.py','game/entities/base/thinking.py','game/entities/base/aging.py',
    'game/entities/base/visible.py','game/entities/base/pockets.py',
    'game/world/world.py','game/world/time_system.py','game/world/entity_gen.py',
]
skip = {'__init__','__str__','__repr__','__contains__','__post_init__','__hash__','__eq__','__len__','__lt__','__le__',
    'serialize','on_hour','on_hour_end','on_arrival','on_dawn','build_schedule',
    'die','start_action','check_for_encounters','react_to_encounter',
    'resolve_engagement','update_movement','process_aging','process_ruins',
    'is_passable','get_lifespan','get_ruins_duration','on_old_age_death','get_tiles','occupies'}

all_py = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__','node_modules','.git')]
    for f in files:
        if f.endswith('.py'):
            all_py.append(os.path.join(root, f).replace('\\', '/'))

fc = {}
for fp in all_py:
    with open(fp, encoding='utf-8') as fh:
        fc[fp] = fh.readlines()

defs = []
for af in audit_files:
    fp = './' + af
    if fp not in fc:
        print(f"MISSING: {af}")
        continue
    prev = ''
    for i, line in enumerate(fc[fp], 1):
        s = line.strip()
        m = re.match(r'def\s+(\w+)\s*\(', s)
        if m:
            name = m.group(1)
            if name not in skip and '@property' not in prev and '.setter' not in prev:
                defs.append((af, i, name))
        prev = s

print(f'Checking {len(defs)} methods...')

results = []
for af, ln, name in defs:
    pat = re.compile(r'(?<!\w)' + re.escape(name) + r'\s*\(')
    apat = re.compile(r'\.\s*' + re.escape(name) + r'\s*=')
    sites = []
    for fp, lines in fc.items():
        rp = fp[2:]  # strip ./
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            if pat.search(s):
                if s.startswith('def ') and name in s.split('(')[0]:
                    continue
                if s.startswith('from ') or s.startswith('import '):
                    continue
                if apat.search(s):
                    continue
                sites.append(f'{rp}:{i}')
    if len(sites) == 1:
        results.append(f'{af}:{ln} def {name} - 1 call site - [{sites[0]}]')

print(f'\nMethods with EXACTLY 1 call site: {len(results)}\n')
for r in results:
    print(r)
