#!/usr/bin/env python3
"""Track new Delhi/Gurgaon finance jobs from LinkedIn's public search. Excludes Noida.
Writes data/seen-jobs.json (state), data/new-jobs-<date>.md (report) and appends new
candidates to data/pipeline.md. Read-only against LinkedIn; nothing is applied to."""
import re, json, time, html, subprocess, urllib.parse, datetime, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEN = f"{ROOT}/data/seen-jobs.json"
TODAY = datetime.date.today().isoformat()
KW = ["Senior FP&A","FP&A Manager","Financial Planning and Analysis","Finance Business Partner","Business Analyst finance","MIS Analyst","Financial Analyst","Management Reporting","Commercial Finance","Financial Planning Analyst","Senior Financial Analyst","Business Finance"]
LOCS = ["New Delhi, Delhi, India","Gurugram, Haryana, India"]
POS = re.compile(r"fp&a|fpa|financial planning|business partner|financial analyst|finance analyst|business analyst|\bmis\b|management report|financial report|commercial finance|business finance|planning|budget|forecast|finance manager|analyst", re.I)
NEG = re.compile(r"intern\b|internship|trainee|fresher|junior|jr\b|data scientist|software|engineer|developer|sales|marketing|\bhr\b|recruit|credit|risk|devops|product analyst|operations analyst|scrum|salesforce|sap |security|\bqa\b|\btax\b|audit|accounts payable|accounts receivable|payroll|data analyst|bi analyst|business intelligence", re.I)
ABOVE = re.compile(r"senior manager|\bavp\b|vice president|\bvp\b|director|head of|general manager|\bdgm\b|\bagm\b|associate director|controller", re.I)
LOC = re.compile(r"delhi|gurgaon|gurugram", re.I)
def curl(u):
    return subprocess.run(["curl","-sS","-m","25","-A","Mozilla/5.0",u],capture_output=True,text=True).stdout
def search():
    out = {}
    for loc in LOCS:
        for kw in KW:
            for start in (0, 25):
                u = "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode({"keywords":kw,"location":loc,"f_TPR":"r2592000","start":start})
                for c in re.split(r'<li>\s*<div class="base-card', curl(u))[1:]:
                    g = lambda p: (re.search(p, c, re.S) or [None, ""])[1]
                    link = g(r'href="(https://[a-z.]*linkedin.com/jobs/view/[^"?]*)')
                    if not link: continue
                    out[link] = dict(title=html.unescape(g(r'base-search-card__title">\s*(.*?)\s*<').strip()),
                        company=html.unescape(re.sub(r'<.*?>','',g(r'base-search-card__subtitle">(.*?)</h4>')).strip()),
                        location=html.unescape(g(r'job-search-card__location">\s*(.*?)\s*<').strip()),
                        url=link, posted=g(r'datetime="([^"]*)"'))
                time.sleep(1.5)
    return out
def detail(u):
    t = curl(u)
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', t, re.S)
    d = html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',m.group(1)))) if m else ""
    yrs = ["-".join(x for x in y if x) for y in re.findall(r'(\d{1,2})\s*(?:\+|-|to|–)?\s*(\d{1,2})?\s*\+?\s*(?:years|yrs)', d, re.I)[:3]]
    must = bool(re.search(r'(must have|mandatory|required)[^.]{0,60}\b(CA|CPA|ACCA|CMA|MBA|chartered)\b|\b(CA|CPA|ACCA|CMA|MBA|chartered accountant)\b[^.]{0,40}(required|must|mandatory)', d, re.I))
    quals = sorted(set(k.upper() for k in re.findall(r'\b(CA|CPA|ACCA|CMA|MBA|CFA|Chartered Accountant)\b', d, re.I)))
    tools = sorted(set(k for k in re.findall(r'\b(SQL|Power BI|Tableau|Hyperion|Anaplan|SAP|Oracle|Python|Excel|Workday|Adaptive)\b', d)))
    return dict(len=len(d), yrs=yrs, quals=quals, qual_required=must, tools=tools)
def main():
    seen = json.load(open(SEEN)) if os.path.exists(SEEN) else {}
    found = search()
    cand = {u:j for u,j in found.items() if LOC.search(j["location"]) and not re.search("noida", j["location"], re.I) and POS.search(j["title"]) and not NEG.search(j["title"])}
    new = {u:j for u,j in cand.items() if u not in seen}
    for u,j in new.items():
        j["band"] = "above" if ABOVE.search(j["title"]) else "in-range"
        if j["band"]=="in-range": j.update(detail(u)); time.sleep(1.2)
    for u,j in found.items(): seen.setdefault(u, dict(title=j["title"], company=j["company"], first_seen=TODAY))
    json.dump(seen, open(SEEN,"w"), indent=1)
    rows = sorted(new.values(), key=lambda j:(j.get("qual_required",False), j["posted"]))
    lines = [f"# New jobs {TODAY}: Delhi and Gurgaon (Noida excluded)\n", f"Searched {len(found)} postings from the last 30 days. {len(cand)} matched filters. **{len(new)} are new** since the last run.\nLinkedIn only: confirm each on the employer's careers page. No salary is stated in most.\n"]
    ir = [j for j in rows if j["band"]=="in-range"]; ab = [j for j in rows if j["band"]=="above"]
    lines.append(f"## In your range ({len(ir)})\n\n| Role | Company | Where | Posted | Experience | Quals | Tools | Link |\n|---|---|---|---|---|---|---|---|")
    for j in ir:
        q = (("**REQUIRED** " if j.get("qual_required") else "") + ", ".join(j["quals"])) if j.get("quals") else "none seen"
        lines.append(f"| {j['title']} | {j['company']} | {j['location']} | {j['posted']} | {', '.join(j.get('yrs',[])) or 'n/s'} | {q} | {', '.join(j.get('tools',[])) or '-'} | {j['url']} |")
    lines.append(f"\n## Above your band, manager level and up ({len(ab)})\n")
    for j in ab: lines.append(f"- {j['title']} | {j['company']} | {j['location']} | {j['posted']} | {j['url']}")
    open(f"{ROOT}/data/new-jobs-{TODAY}.md","w").write("\n".join(lines)+"\n")
    p = f"{ROOT}/data/pipeline.md"; t = open(p).read()
    add = "".join(f"- [ ] {j['url']} | {j['company']} | {j['title']}\n" for j in ir if not j.get("qual_required"))
    if add and "## Pending" in t: t = t.replace("## Pending\n", "## Pending\n"+add, 1); open(p,"w").write(t)
    print(json.dumps(dict(found=len(found), matched=len(cand), new=len(new), in_range=len(ir), above=len(ab))))
main()
