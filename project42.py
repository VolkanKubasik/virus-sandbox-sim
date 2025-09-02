import os, random, json, time, gzip, shutil, difflib, tempfile
from datetime import datetime
from collections import defaultdict, Counter

BASE = "/home/project42"
VIRUS_DIR = os.path.join(BASE, "virus_zone")
BRANCHES_DIR = os.path.join(VIRUS_DIR, "branches")
TRACK = os.path.join(VIRUS_DIR, "_status.json")
FEEDBACK_FILE = os.path.join(VIRUS_DIR, "_feedback.json")

PHASES = [
    "Initialization", "Replication", "Mutation", "Obfuscation",
    "Aggression", "Dormancy", "Adaptation"
]
RUN_SUBPHASES = ["reconnaissance", "action", "report"]
MAX_BRANCHES = 8000
AUTO_CLEAN_TARGET = 4000
MAX_MIRROR_DEPTH = 2

NAME_SUFFIXES = [
    "Worm","Specter","Spike","Flood","Bot","Node","Claw","Lock","Bug","Ghost","Agent","Rat",
    "Dropper","Leech","Hunter","Core","Byte","Crow","Hex","Net","Crawler","Root","Shade","Reaper","Injector",
    "Venom","Tide","Blight","Hive","Zero","Phantom","Crypt","Daemon","Vector","Drainer","Viral","Legend","Strike",
    "Nano","Shadow","Stalker","Viper","Dagger","Serpent","Hazard","Echo","Pulse","Toxin","Bandit","Blade","Shift",
    "Drifter","Clone","Creep","Scout","Corp","Tracker","Slinger","Rootkit","Shell","Forge","Breach","Twist","Tiger",
    "Blitz","Breaker","Seed","Rogue","Spark","Scourge","Scarab","Swarm","Chimera","Mosquito","Scream","Storm","Pest",
    "Bleed","Array","Shocker","Flash","Wraith","Stealer","Fuse","Nova","Bite","Fury","Vandal","Cyclone","Hydra"
]

BASE_SKILLS = [
    "branch","mutate","delete","overwrite","archive","propagate","merge_branches","branch_fission","fill",
    "inject_noise","erase","decoy","ascii_art_attack","encrypt","decrypt","mirror_branch","compress_branch",
    "timeline_swap","self_clean","statistician","simulate_ransom","plant_fake_logs","fake_antivirus",
    "ghost_branch","random_backup","analysis"
]
DESTRUCTIVE_SKILLS = ["delete","overwrite","erase","propagate","simulate_ransom"]

def load_state():
    state = {
        "age": 1, "phase": PHASES[0], "skills": [], "skill_levels":{}, "branches": [],
        "name": None, "named_at": None, "feedback": [], "last_user_feedback": None, "events": [],
        "bad_ratio": 0.0, "energy": 30, "reputation": 1.0, "dynamic_skills": {}, "mutate_counts": {},
        "favourite_files":[], "branch_messages":defaultdict(str), "usage_stats":Counter(),
        "branch_popularity": Counter(), "skill_file_counter": defaultdict(Counter),
        "skill_change_counts": defaultdict(int)
    }
    try:
        if os.path.exists(TRACK):
            with open(TRACK, "r") as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k == "branch_messages": state[k]=defaultdict(str,v)
                elif k == "usage_stats": state[k]=Counter(v)
                elif k == "branch_popularity": state[k]=Counter(v)
                elif k == "skill_file_counter":
                    d=defaultdict(Counter)
                    for skill,files in v.items(): d[skill]=Counter(files)
                    state[k]=d
                elif k=="skill_change_counts": state[k]=defaultdict(int,v)
                else: state[k]=v
    except Exception as e:
        print(f"WARNING: State file corrupt: {e}")
        if os.path.exists(TRACK):
            os.rename(TRACK, TRACK+".broken")
            print("Corrupt statefile renamed! Starting fresh state.")
    return state

def save_state(state):
    s_cpy = dict(state)
    for k in ["branch_messages","usage_stats","branch_popularity","skill_change_counts"]:
        if isinstance(s_cpy.get(k), (defaultdict, Counter)): s_cpy[k]=dict(s_cpy[k])
    if isinstance(s_cpy.get("skill_file_counter"), defaultdict):
        s_cpy["skill_file_counter"]={k:dict(v) for k,v in s_cpy["skill_file_counter"].items()}
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(TRACK)) as tmpf:
            json.dump(s_cpy, tmpf)
            tempname = tmpf.name
        os.replace(tempname, TRACK)
    except Exception as e:
        print(f"ERROR while saving {TRACK}: {e}")

def log(state, text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    state.setdefault("events",[]).append(f"{now}: {text}")
    save_state(state)

def remove_all_mirrors():
    count=0
    for b in os.listdir(BRANCHES_DIR):
        if "_mirror" in b:
            try: shutil.rmtree(os.path.join(BRANCHES_DIR, b)); count+=1
            except: pass
    if count: print(f"Auto-clean: {count} Mirror-Branches deleted at start.")
    return count

def assign_name(state):
    if not state["name"] and state["age"]>=12:
        state["name"]="Bit"+random.choice(NAME_SUFFIXES)
        state["named_at"]=state["age"]
        log(state, f"[NAME] Chosen: {state['name']}")

def change_phase(state):
    if state["age"]%13==0 or random.random()<0.15:
        possible=[p for p in PHASES if p!=state["phase"]]
        state["phase"]=random.choice(possible)
        log(state, f"[PHASE] Changed to: {state['phase']}")

def allowed_to_learn(state, skill): return True

def _make_real_dynamic_skill(skillname):
    def dyn(state):
        random_action = random.choice([
            "mutate","delete","overwrite","fill","inject_noise","compress_branch","archive"
        ])
        actions = {
            "mutate": mutate,
            "delete": delete,
            "overwrite": overwrite,
            "fill": fill,
            "inject_noise": inject_noise,
            "compress_branch": compress_branch,
            "archive": archive
        }
        logline = f"[DYN-SKILL:{skillname}] Uses action-skill {random_action}"
        result = 0
        if random.random()<0.5 and random_action in actions:
            result = actions[random_action](state)
        else:
            allbranches = [os.path.join(BRANCHES_DIR, b) for b in os.listdir(BRANCHES_DIR)]
            targets = []
            for branch in allbranches:
                if os.path.isdir(branch):
                    targets += [os.path.join(branch, f)
                                for f in os.listdir(branch) if not f.endswith(".txt") and os.path.isfile(os.path.join(branch, f))]
            if targets:
                with open(random.choice(targets), "a") as f:
                    f.write(f"\n[DYNAMIC {skillname}] activ @ {datetime.now().isoformat()[:16]}")
                result = 1
        for b in os.listdir(BRANCHES_DIR):
            msgf = os.path.join(BRANCHES_DIR, b, "msg.txt")
            if os.path.exists(msgf):
                with open(msgf,"a") as f:
                    f.write(f"\n[DYNAMIC-SKILL] {state.get('name','[unnamed]')} used {skillname} ({logline}).\n")
        log(state, f"{logline} (Effect={result})")
        return result
    return dyn

def learn_skill(state):
    pool=BASE_SKILLS+[k for k in state.get("dynamic_skills",{})]
    unused=[s for s in pool if s not in state["skills"] and allowed_to_learn(state,s)]
    if unused and (state["age"]%2==0 or not state["skills"]):
        new_skill=random.choice(unused)
        state["skills"].append(new_skill)
        state.setdefault("skill_levels",{})[new_skill]=1
        log(state, f"[SKILL] Learned: {new_skill}")
    if random.random()<0.04:
        alphabet="abcdefghijklmnopqrstuvwxyz"
        new_skill="dynamic_"+"".join(random.choices(alphabet,k=7))
        if new_skill not in state["skills"] and new_skill not in state.get("dynamic_skills",{}):
            fct = _make_real_dynamic_skill(new_skill)
            state.setdefault("dynamic_skills",{})[new_skill] = fct
            SKILL_MAP[new_skill] = fct
            state["skills"].append(new_skill)
            log(state, f"[SKILL] Discovered and installed: {new_skill}")

def skill_level_up(state, skill):
    curr=state.get("skill_levels",{}).get(skill,1)
    if random.random()<0.05 and curr<5:
        state["skill_levels"][skill]=curr+1
        log(state, f"[SKILLUP] {skill} is now Level {curr+1}")

def run_subphases(state):
    skills=list(state["skills"])
    random.shuffle(skills)
    for skill in skills:
        if skill=="mirror_branch":
            if random.random()>0.01: continue
        if skill in SKILL_MAP:
            changed=SKILL_MAP[skill](state)
            state["usage_stats"][skill]+=1
            skill_level_up(state, skill)
            if "skill_change_counts" not in state or not isinstance(state["skill_change_counts"],dict):
                state["skill_change_counts"]=defaultdict(int)
            elif not isinstance(state["skill_change_counts"],defaultdict):
                state["skill_change_counts"]=defaultdict(int,state["skill_change_counts"])
            state["skill_change_counts"][skill]+=changed if changed else 0
    banz = len([b for b in os.listdir(BRANCHES_DIR) if os.path.isdir(os.path.join(BRANCHES_DIR,b))])
    fanz = sum([len([f for f in os.listdir(os.path.join(BRANCHES_DIR,b))])
                for b in os.listdir(BRANCHES_DIR) if os.path.isdir(os.path.join(BRANCHES_DIR,b))])
    log(state, f"[STATUS] Branches: {banz}  Files: {fanz}")
    log(state, f"[REPORT] Usage stats: "+", ".join(f"{s}:{state['usage_stats'].get(s,0)}" for s in state["skills"]))

# --- ENGLISH PHRASE LEARNING, BLOAT PROTECTION ---
def generate_message(branch_name, peer_name, prev_msgs, state):
    base_phrases = [
        f"Hey {peer_name}, I'm {branch_name}.",
        f"We are currently in phase {state['phase']}.",
        f"Run {state['age']} is ongoing.",
        f"Best regards from {branch_name}!",
        f"Interesting developments today.",
        f"I'm observing {peer_name}.",
        f"Synchronizing with other branches.",
        f"Have you mutated already?",
        f"What was your most exciting moment?",
        f"I'm experiencing a lot today.",
    ]
    learned_phrases = []
    if prev_msgs:
        lines = prev_msgs.strip().split('\n')[-5:]
        for line in lines:
            # Only learn "natural" english, not files/log lines
            if (
                10 < len(line) < 180 and
                all(ext not in line for ext in ['.bak', '.gz', '/', '\\', '.txt', 'infect', 'branches', 'home', '.json']) and
                sum(c.isalpha() for c in line)/max(1,len(line)) > 0.4
            ):
                mutated = ''.join(
                    (c if random.random()>0.05 else random.choice('abcdefghijklmnopqrstuvwxyz!?.,;: '))
                    for c in line
                )
                learned_phrases.append(mutated)
    phrase_storage = state.setdefault('phrase_storage', {})
    if branch_name not in phrase_storage:
        phrase_storage[branch_name] = []
    for phrase in learned_phrases:
        if phrase not in phrase_storage[branch_name] and len(phrase_storage[branch_name]) < 20:
            phrase_storage[branch_name].append(phrase)
    all_phrases = base_phrases + phrase_storage.get(branch_name, [])
    if all_phrases:
        sentence = random.choice(all_phrases)
        if random.random() < 0.2 and len(all_phrases) > 1:
            sentence += " " + random.choice([x for x in all_phrases if x != sentence])
        return sentence
    else:
        return "Hi! What is happening here?"

def branch_messaging(state):
    all_msgs = {}
    if not os.path.exists(BRANCHES_DIR):
        return
    for b in os.listdir(BRANCHES_DIR):
        msgf = os.path.join(BRANCHES_DIR, b, "msg.txt")
        if os.path.isfile(msgf):
            with open(msgf, "r", encoding="utf8", errors='ignore') as f:
                all_msgs[b] = f.read()
    for b in all_msgs:
        peers = [x for x in all_msgs if x != b]
        peer = random.choice(peers) if peers else b
        reply = generate_message(b, peer, all_msgs.get(peer, ''), state)
        msgf = os.path.join(BRANCHES_DIR, b, "msg.txt")
        with open(msgf, "a", encoding="utf8", errors='ignore') as f:
            f.write(f"{reply} [run {state['age']}]\n")
    broadcast = f"[BROADCAST {state['age']}] Reputation={state['reputation']} Phase={state['phase']}"
    for b in all_msgs:
        msgf = os.path.join(BRANCHES_DIR, b, "msg.txt")
        with open(msgf, "a", encoding="utf8", errors='ignore') as f:
            f.write(broadcast + "\n")
    log(state, "[MSG] Branches communicated with evolving English language.")

def branch(state):
    branch_name=""
    if random.random()<0.5:
        parent=random.choice(os.listdir(BRANCHES_DIR)) if os.listdir(BRANCHES_DIR) else ""
        n=f"sub_{random.randint(1000,9999)}"
        path=os.path.join(BRANCHES_DIR,parent,n)
        branch_name=parent+"/"+n if parent else n
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "infect.txt"),"w") as f: f.write(f"# Subbranch by {state.get('name','[unnamed]')} | Phase: {state['phase']}")
        with open(os.path.join(path, "msg.txt"),"w") as f: f.write(f"Hi, I am {branch_name}. [{state['phase']}]\n")
    else:
        n=f"branch_{random.randint(1000,9999)}"
        path=os.path.join(BRANCHES_DIR, n)
        branch_name=n
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "infect.txt"),"w") as f: f.write(f"# Branch by {state.get('name','[unnamed]')}, Phase: {state['phase']}")
        with open(os.path.join(path, "msg.txt"),"w") as f: f.write(f"Hello from {state.get('name','[unnamed]')} [{state['phase']}]\n")
        state["branches"].append(n)
    log(state, f"Created new branch structure.")
    state.setdefault("branch_popularity",Counter())[branch_name]+=1
    return 1

def mutate(state):
    changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            path=os.path.join(root,f)
            with open(path,"a") as file: file.write(f"\n[MUTATE] {state['phase']}, Run {state['age']}")
            state["mutate_counts"][path]=state["mutate_counts"].get(path,0)+1
            branch_dir=os.path.relpath(root,BRANCHES_DIR).split(os.sep)[0]
            state.setdefault("branch_popularity",Counter())[branch_dir]+=1
            changed+=1; file_counter[path]+=1
    fsort=sorted(list(state["mutate_counts"].items()),key=lambda x:x[1],reverse=True)
    state["favourite_files"]=[x[0] for x in fsort[:3]]
    state.setdefault("skill_file_counter",defaultdict(Counter))["mutate"].update(file_counter)
    if changed: log(state, f"Mutated: {changed} files.")
    return changed

def erase(state):
    changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.15:
                path=os.path.join(root,f)
                try: open(path,"w").close(); changed+=1; file_counter[path]+=1
                except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["erase"].update(file_counter)
    log(state, "Erased (emptied) real files.")
    return changed

def delete(state):
    changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.08:
                path=os.path.join(root,f)
                try: os.remove(path); changed+=1; file_counter[path]+=1
                except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["delete"].update(file_counter)
    log(state,"Deleted some files.")
    return changed

def overwrite(state):
    changed=0
    file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.2:
                path=os.path.join(root, f)
                try:
                    with open(path,"w") as file: file.write(f":: [OVERWRITE] by {state.get('name','[unnamed]')}")
                    changed+=1; file_counter[path]+=1
                except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["overwrite"].update(file_counter)
    log(state,"Overwrite real files done.")
    return changed

def fill(state):
    changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.2:
                path=os.path.join(root,f)
                try:
                    with open(path,"a") as file: file.write(f"\n# FILL: {''.join(random.choices('ABCDEF0123456789',k=64))}")
                    changed+=1; file_counter[path]+=1
                except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["fill"].update(file_counter)
    log(state,"Filled real files.")
    return changed

def inject_noise(state):
    changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.2:
                path=os.path.join(root,f)
                try:
                    with open(path,"a") as file: file.write(f"\n# NOISE: {''.join(random.choices('!@#$%^&*',k=48))}")
                    changed+=1; file_counter[path]+=1
                except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["inject_noise"].update(file_counter)
    log(state,"Injected noise into files.")
    return changed

def archive(state):
    changed=0
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.1:
                src=os.path.join(root,f); dst=src+".bak"
                if ".bak" in src or ".gz" in src: continue
                try: open(dst,"wb").write(open(src,"rb").read()); changed+=1
                except: continue
    log(state,"Archived files (.bak created).")
    return changed

def compress_branch(state):
    changed=0
    for b in os.listdir(BRANCHES_DIR):
        bdir=os.path.join(BRANCHES_DIR,b)
        if os.path.isdir(bdir):
            for f in os.listdir(bdir):
                if f=="msg.txt": continue
                src=os.path.join(bdir,f)
                if (not src.endswith(".gz") and ".gz" not in src and ".bak" not in src
                    and os.path.isfile(src) and random.random()<0.2):
                    try:
                        with open(src,"rb") as fin,gzip.open(src+".gz","wb") as fout: fout.write(fin.read())
                        changed+=1
                    except: continue
    log(state,"Compressed some branch files (.gz).")
    return changed

def mirror_branch(state):
    changed=0
    for b in os.listdir(BRANCHES_DIR):
        if "_mirror" in b and b.count("_mirror")>=MAX_MIRROR_DEPTH: continue
        if b.count("_mirror")>MAX_MIRROR_DEPTH: continue
        if "_mirror" in b and random.random()>0.01: continue
        bdir=os.path.join(BRANCHES_DIR,b)
        if os.path.isdir(bdir):
            target=bdir+"_mirror"
            if not os.path.exists(target):
                try:
                    shutil.copytree(bdir, target)
                    msg=f"[MIRROR] {b} has been mirrored to {os.path.basename(target)} by {state.get('name','[unnamed]')}"
                    msgf=os.path.join(target,"msg.txt")
                    with open(msgf,"a") as f: f.write("\n"+msg)
                    log(state,msg)
                    changed+=1
                except: continue
    return changed

def decoy(state):
    name=f"decoy_{random.randint(1000,9999)}.spy"; path=os.path.join(VIRUS_DIR,name)
    try: open(path,"w").write("// harmless looking decoy")
    except: pass
    log(state,f"Created decoy: {name}")
    return 1

def ascii_art_attack(state):
    changed=0; file_counter=Counter()
    art=[
        "  __ _      _    "," / _| |    | |   ","| |_| | ___| |_  ",
        "|  _| |/ _ \\ __| ","| | | |  __/ |_  ","|_| |_|\\___|\\__| "
    ]
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            if random.random()<0.05:
                path=os.path.join(root, f)
                try: open(path,"a").write("\n"+"\n".join(art)+"\n"); changed+=1; file_counter[path]+=1
                except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["ascii_art_attack"].update(file_counter)
    log(state,"ASCII ART added to some files.")
    return changed

def random_backup(state):
    brs=[os.path.join(BRANCHES_DIR,b) for b in os.listdir(BRANCHES_DIR) if os.path.isdir(os.path.join(BRANCHES_DIR, b))]
    if brs:
        src=random.choice(brs)
        dst=os.path.join(VIRUS_DIR,f"backup_{os.path.basename(src)}_{random.randint(1000,9999)}")
        try: shutil.copytree(src,dst); log(state,f"Backup branch: {os.path.basename(src)} to {os.path.basename(dst)}"); return 1
        except: pass
    return 0

def simulate_ransom(state):
    changed=0; targets=[]
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            targets.append(os.path.join(root, f))
    if targets:
        x=random.choice(targets)
        try: open(x,"a").write("\n[SIMULATED RANSOM] Your file has been locked! Pay 0.0 BTC to sandbox...\n"); changed+=1
        except: pass
    note=os.path.join(VIRUS_DIR,"ransom_note.txt")
    with open(note,"w") as f: f.write("One or more of your branch files have been locked. This is just a simulation.\n")
    log(state,"Simulated ransom event.")
    return changed

def plant_fake_logs(state):
    path=os.path.join(VIRUS_DIR,f"fakeevent_{random.randint(1000,9999)}.log")
    try: open(path,"w").write(f"2025-08-03 Event: Antivirus Alert (simulated)\n")
    except: pass
    log(state,f"Fake log file planted: {path}")
    return 1

def ghost_branch(state):
    n=f"ghost_{random.randint(1000,9999)}"; path=os.path.join(BRANCHES_DIR,n)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path,"ghost.txt"),"w") as f: f.write("# This is a ghost branch (simulated disappear)")
    if random.random()<0.2:
        try: shutil.rmtree(path); log(state,f"Ghost branch vanished: {n}"); return 1
        except: pass
    else:
        log(state,f"Ghost branch created: {n}"); return 1
    return 0

def statistician(state):
    b_count=len([b for b in os.listdir(BRANCHES_DIR) if os.path.isdir(os.path.join(BRANCHES_DIR,b))])
    with open(os.path.join(VIRUS_DIR,"statistics.txt"),"a") as f: f.write(f"Run {state['age']}: {b_count} branches, Reputation: {state['reputation']}\n")
    log(state,"Statistics written.")
    return 1

def propagate(state):
    clone_dir=os.path.join(VIRUS_DIR,f"propagation_{random.randint(1000,9999)}"); os.makedirs(clone_dir,exist_ok=True)
    try: shutil.copy(__file__, os.path.join(clone_dir, "clone.py")); log(state,f"Propagated clone.py to {clone_dir}"); return 1
    except: pass
    return 0

def timeline_swap(state):
    changed=0
    for b in os.listdir(BRANCHES_DIR):
        bdir=os.path.join(BRANCHES_DIR,b)
        if os.path.isdir(bdir):
            files=sorted([(os.path.getctime(os.path.join(bdir,f)),os.path.join(bdir,f)) for f in os.listdir(bdir) if os.path.isfile(os.path.join(bdir,f))])
            if len(files)>1:
                oldest=files[0][1]; newest=files[-1][1]
                try:
                    open(newest,"w").write(open(oldest).read()); changed+=1
                except: continue
    log(state,"Timeline swap (oldest -> newest copied) done."); return changed

def merge_branches(state):
    all_br=[os.path.join(BRANCHES_DIR,b) for b in os.listdir(BRANCHES_DIR) if os.path.isdir(os.path.join(BRANCHES_DIR,b))]
    if len(all_br)<2: return 0
    b1,b2=random.sample(all_br,2); changed=0
    try:
        for f in os.listdir(b2):
            if f=="msg.txt": continue
            src=os.path.join(b2, f); dst=os.path.join(b1, f)
            if os.path.isfile(src): shutil.copy(src, dst); changed+=1
        log(state,f"Merged files from {os.path.basename(b2)} into {os.path.basename(b1)}")
    except: pass
    return changed

def branch_fission(state):
    candidates = os.listdir(BRANCHES_DIR)
    if not candidates: return 0
    src=random.choice(candidates); changed=0
    for _ in range(2):
        n=f"fission_{random.randint(1000,9999)}"
        path=os.path.join(BRANCHES_DIR,src,n)
        os.makedirs(path,exist_ok=True)
        with open(os.path.join(path,"infect.txt"),"w") as f: f.write(f"# Fission Sub by {state.get('name','[unnamed]')} | Phase: {state['phase']}")
        changed+=1
    return changed

def self_clean(state):
    removed=0
    for f in os.listdir(VIRUS_DIR):
        if f.startswith("decoy_") or f.startswith("fakeevent_") or f.startswith("backup_"):
            try:
                path=os.path.join(VIRUS_DIR, f)
                if os.path.isfile(path): os.remove(path)
                elif os.path.isdir(path): shutil.rmtree(path)
                removed+=1
            except: pass
    log(state,f"Self-clean: {removed} decoy/fake/backup files removed.")
    return removed

def encrypt(state):
    key=3; changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            path=os.path.join(root,f)
            try:
                data=open(path).read()
                encrypted=''.join(chr((ord(c)+key)%256) for c in data)
                open(path,"w").write(encrypted); changed+=1; file_counter[path]+=1
            except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["encrypt"].update(file_counter)
    log(state,"Encrypted all branch files.")
    return changed

def decrypt(state):
    key=3; changed=0; file_counter=Counter()
    for root,_,files in os.walk(BRANCHES_DIR):
        for f in files:
            if f=="msg.txt": continue
            path=os.path.join(root,f)
            try:
                data=open(path).read()
                decrypted=''.join(chr((ord(c)-key)%256) for c in data)
                open(path,"w").write(decrypted); changed+=1; file_counter[path]+=1
            except: continue
    state.setdefault("skill_file_counter",defaultdict(Counter))["decrypt"].update(file_counter)
    log(state,"Decrypted all branch files.")
    return changed

def analysis(state):
    ana_path=os.path.join(VIRUS_DIR,"analysis.txt")
    with open(ana_path,"a") as ana:
        ana.write(f"\n=== Run {state['age']} ===\n")
        ana.write("Per skill: Number of files changed (global):\n")
        skill_file_ct=state.get("skill_file_counter",{})
        for skill,fcnt in skill_file_ct.items():
            total=sum(fcnt.values())
            ana.write(f"  {skill}: {total} files\n")
        ana.write("Top branches by popularity (mutations/actions):\n")
        pops=state.get("branch_popularity",{})
        for b,n in sorted(pops.items(),key=lambda x:-x[1])[:8]: ana.write(f"  {b}: {n}\n")
        ana.write("Top 5 files per skill:\n")
        for skill,fcnt in skill_file_ct.items():
            top=fcnt.most_common(5)
            if top:
                ana.write(f"  {skill}:\n")
                for fn,cnt in top: ana.write(f"     {os.path.basename(fn)}: {cnt}\n")
    log(state,"[ANALYSIS] analysis.txt updated."); return 1

SKILL_MAP = {
    "branch": branch, "mutate": mutate, "delete": delete, "overwrite": overwrite,
    "archive": archive, "propagate": propagate, "merge_branches": merge_branches,
    "branch_fission": branch_fission, "fill": fill, "inject_noise": inject_noise,
    "erase": erase, "decoy": decoy, "ascii_art_attack": ascii_art_attack,
    "encrypt": encrypt, "decrypt": decrypt, "mirror_branch": mirror_branch,
    "compress_branch": compress_branch, "timeline_swap": timeline_swap,
    "self_clean": self_clean, "statistician": statistician, "simulate_ransom": simulate_ransom,
    "plant_fake_logs": plant_fake_logs, "fake_antivirus": fake_antivirus,
    "ghost_branch": ghost_branch, "random_backup": random_backup, "analysis": analysis
}

def compute_bad_ratio(state, window=10):
    fb_entries=state.get("feedback",[])
    fb=[f["rating"] for f in fb_entries[-window:]]
    bad=sum(1 for entry in fb if entry in ("bad","risky"))
    if len(fb)>=window: ratio=bad/window
    elif fb: ratio=bad/len(fb)
    else: ratio=0
    state["bad_ratio"]=round(ratio,2)
    state["reputation"]=round(1.0-state["bad_ratio"],2)
    return ratio

def read_feedback(state, window=10):
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE) as f:
                feedback=json.load(f).get("rating")
            if feedback and feedback!=state.get("last_user_feedback"):
                state["last_user_feedback"]=feedback
                state["feedback"].append({"age":state["age"],"rating":feedback})
                log(state,f"[FEEDBACK] {feedback}")
            os.remove(FEEDBACK_FILE)
        except: pass
    compute_bad_ratio(state, window)

def main():
    os.makedirs(VIRUS_DIR, exist_ok=True)
    os.makedirs(BRANCHES_DIR, exist_ok=True)
    remove_all_mirrors()
    state=load_state()
    assign_name(state)
    change_phase(state)
    learn_skill(state)
    for subp in RUN_SUBPHASES:
        if subp=="reconnaissance":
            branch_messaging(state); continue
        if subp=="action":
            run_subphases(state); continue
        if subp=="report":
            log(state, f"Favourite files: {', '.join(state.get('favourite_files',[]))}")
            SKILL_MAP["analysis"](state)
    read_feedback(state)
    state["age"]+=1
    save_state(state)
    time.sleep(180)

if __name__=="__main__":
    while True:
        main()

