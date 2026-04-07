#!/usr/bin/env python3
import os
import sys
import re
import time
from typing import Dict, List

import polib
try:
    from deep_translator import GoogleTranslator
except Exception as e:
    print("ERROR: deep_translator is not installed. Please install it first.")
    sys.exit(1)

PLACEHOLDER_PATTERN = re.compile(r"%\([a-zA-Z_][a-zA-Z0-9_]*\)s|%s")


def protect_placeholders(text: str):
    if not text:
        return text, {}
    mapping: Dict[str, str] = {}
    def repl(match):
        ph = match.group(0)
        token = f"__PH_{len(mapping)}__"
        mapping[token] = ph
        return token
    protected = PLACEHOLDER_PATTERN.sub(repl, text)
    return protected, mapping


def unprotect_placeholders(text: str, mapping: Dict[str, str]):
    if not text or not mapping:
        return text
    for token, ph in mapping.items():
        text = text.replace(token, ph)
    return text


def translate_text(text: str, translator: GoogleTranslator) -> str:
    if text is None:
        return ""
    if text == "":
        return ""
    # protect placeholders
    protected, mapping = protect_placeholders(text)
    translated = None
    try:
        translated = translator.translate(protected)
    except Exception:
        # backoff and retry once
        time.sleep(1.0)
        try:
            translated = translator.translate(protected)
        except Exception:
            translated = None
    if not translated:
        translated = protected
    # unprotect
    translated = unprotect_placeholders(translated, mapping)
    return translated or ""


def coalesce(s: str, fallback: str) -> str:
    if s is None or s == "":
        return fallback or ""
    return s


def process_language(lang: str, target: str) -> None:
    po_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
    if not os.path.isfile(po_path):
        print(f"skip {lang}: {po_path} not found")
        return
    po = polib.pofile(po_path)
    total = len(po)
    print(f"Processing {lang}: entries={total}")

    translator = GoogleTranslator(source='auto', target=target)

    changed = 0
    start_time = time.time()

    for idx, entry in enumerate(po):
        # skip header
        if entry.msgid == "":
            continue
        # remove fuzzy flag if present
        if 'fuzzy' in entry.flags:
            entry.flags = [f for f in entry.flags if f != 'fuzzy']
            changed += 1
        try:
            if entry.msgid_plural:
                # ensure msgstr_plural exists as dict
                if entry.msgstr_plural is None:
                    entry.msgstr_plural = {}
                # translate singular form (index 0)
                src0 = entry.msgid
                cur0 = entry.msgstr_plural.get(0)
                if not cur0 or cur0 == src0:
                    t0 = translate_text(src0, translator)
                    entry.msgstr_plural[0] = coalesce(t0, src0)
                    changed += 1
                # translate plural forms using msgid_plural as source
                srcp = entry.msgid_plural
                # handle common plural indexes 1..3 if present
                for k in sorted(list(entry.msgstr_plural.keys()) + [1, 2, 3]):
                    if k == 0:
                        continue
                    curk = entry.msgstr_plural.get(k)
                    if curk is None or curk == "" or curk == srcp:
                        tk = translate_text(srcp, translator)
                        entry.msgstr_plural[k] = coalesce(tk, srcp)
                        changed += 1
            else:
                if not entry.msgstr or entry.msgstr == entry.msgid:
                    t = translate_text(entry.msgid, translator)
                    entry.msgstr = coalesce(t, entry.msgid)
                    changed += 1
        except Exception as e:
            # Print error and continue; also coalesce any None values
            entry.msgstr = coalesce(entry.msgstr, entry.msgid)
            if entry.msgid_plural and entry.msgstr_plural is not None:
                for k, v in list(entry.msgstr_plural.items()):
                    entry.msgstr_plural[k] = coalesce(v, entry.msgid_plural if k else entry.msgid)
            print(f"warn: failed to translate idx={idx}: {e}")
        # periodic save to avoid large loss and to flush None
        if (idx + 1) % 200 == 0:
            # coalesce Nones globally to satisfy polib
            for e2 in po:
                if not e2.msgid_plural:
                    e2.msgstr = coalesce(e2.msgstr, e2.msgid)
                else:
                    if e2.msgstr_plural is None:
                        e2.msgstr_plural = {}
                    for kk, vv in list(e2.msgstr_plural.items()):
                        e2.msgstr_plural[kk] = coalesce(vv, e2.msgid_plural if kk else e2.msgid)
            po.save(po_path)
            elapsed = time.time() - start_time
            print(f"  progress {idx + 1}/{total} in {elapsed:.1f}s, changed={changed}")
            sys.stdout.flush()
    # final coalesce and save
    for e2 in po:
        if not e2.msgid_plural:
            e2.msgstr = coalesce(e2.msgstr, e2.msgid)
        else:
            if e2.msgstr_plural is None:
                e2.msgstr_plural = {}
            for kk, vv in list(e2.msgstr_plural.items()):
                e2.msgstr_plural[kk] = coalesce(vv, e2.msgid_plural if kk else e2.msgid)
    po.save(po_path)
    print(f"Done {lang}. Changed: {changed}")


def main():
    # map language code to deep_translator target
    targets = {
        'en': 'en',
        'zh': 'zh-CN',
    }
    langs: List[str] = []
    # Allow CLI args to specify subset
    if len(sys.argv) > 1:
        langs = sys.argv[1:]
    else:
        langs = ['en', 'zh']
    for lang in langs:
        target = targets.get(lang, lang)
        process_language(lang, target)

if __name__ == '__main__':
    main() 