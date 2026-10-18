import json, locale, os, shutil, subprocess, sys
from importlib.metadata import version


def radon(cmd, path):
    exe = shutil.which("radon") or "radon"
    r = subprocess.run([exe, cmd, "-j", path], capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip():
        return "ERROR rc=%s" % r.returncode
    data = next(iter(json.loads(r.stdout).values()))
    if isinstance(data, dict) and "error" in data:
        return "ERROR " + str(data["error"])[:60]
    return data


for path in sys.argv[1:]:
    out = {}
    try:
        import lizard
        info = lizard.analyze_file(path)
        ccns = [f.cyclomatic_complexity for f in info.function_list]
        out.update(liz_nloc=info.nloc, liz_funcs=len(ccns), liz_ccn_sum=sum(ccns),
                   liz_ccn_max=max(ccns, default=0))
    except Exception as e:
        out["lizard"] = "ERROR " + type(e).__name__
    cc = radon("cc", path)
    if isinstance(cc, str):
        out["radon_cc"] = cc
    else:
        out.update(rad_blocks=len(cc), rad_cc_sum=sum(b["complexity"] for b in cc),
                   rad_cc_max=max((b["complexity"] for b in cc), default=0))
    raw = radon("raw", path)
    if isinstance(raw, str):
        out["radon_raw"] = raw
    else:
        out.update(rad_loc=raw["loc"], rad_sloc=raw["sloc"], rad_lloc=raw["lloc"],
                   rad_comments=raw["comments"], rad_blank=raw["blank"])
    mi = radon("mi", path)
    if isinstance(mi, str):
        out["radon_mi"] = mi
    else:
        out["rad_mi"] = round(mi["mi"], 2)
    print(os.path.basename(path)[:-3] + "|" + json.dumps(out, sort_keys=True))
try:
    print("ENV|py=%s lizard=%s radon=%s enc=%s" % (sys.version.split()[0],
          version("lizard"), version("radon"), locale.getpreferredencoding()))
except Exception as e:
    print("ENV|error " + str(e))
