#!/usr/bin/env python3
"""Run JavaScript in the existing Rediffmail Edge tab without copying cookies.

Requires Edge > View > Developer > Allow JavaScript from Apple Events.
Use --inspect for a bounded DOM/request-path snapshot, or --script FILE.
Script results must be JSON serializable; async scripts must store results in
the page and be polled by subsequent invocations (Apple Events is synchronous).
"""
import argparse
import json
import subprocess
from pathlib import Path


def evaluate(source):
    javascript = "JSON.stringify((()=>{" + source + "})())"
    # JSON string quoting is also valid for these AppleScript string literals.
    script = '''tell application "Microsoft Edge"
repeat with w in windows
repeat with t in tabs of w
if URL of t starts with "https://webmail.rediffmailpro.com/" then
return execute t javascript %s
end if
end repeat
end repeat
error "No Rediffmail tab found in Edge."
end tell''' % json.dumps(javascript)
    result = subprocess.run(["osascript", "-"], input=script, text=True,
                            capture_output=True, timeout=60)
    if result.returncode:
        if "JavaScript through AppleScript is turned off" in result.stderr:
            raise RuntimeError("Enable Edge > View > Developer > Allow JavaScript from Apple Events.")
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


INSPECT = r'''
return {
  title: document.title,
  text: document.body.innerText.slice(0, 20000),
  resources: [...new Set(performance.getEntriesByType('resource')
    .map(x=>new URL(x.name).pathname).filter(x=>x.includes('ajaxprism')))],
  scripts: [...document.scripts].filter(x=>x.src).map(x=>new URL(x.src).pathname),
  scroll: [...document.querySelectorAll('div')]
    .filter(x=>x.clientHeight>250 && x.scrollHeight>x.clientHeight)
    .map(x=>({className:x.className,height:x.clientHeight,total:x.scrollHeight,top:x.scrollTop})),
  controls: [...document.querySelectorAll('button,[role=button],a')].slice(0,150)
    .map(x=>({tag:x.tagName,text:x.innerText,title:x.title,aria:x.getAttribute('aria-label')}))
};
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect', action='store_true')
    mode.add_argument('--script', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(INSPECT if args.inspect else args.script.read_text()), indent=2))
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
