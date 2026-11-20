#!/usr/bin/env python3
"""Read-only EN/JA strict-JSON terminology gate. No translation or automatic repair."""
import argparse
import json
import sys
from pathlib import Path

from terminology import DEFAULT_TERMINOLOGY, check, load, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('target')
    parser.add_argument('--terminology', default=str(DEFAULT_TERMINOLOGY))
    parser.add_argument('--profile')
    parser.add_argument('--application')
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        inputs = [Path(args.source), Path(args.target), Path(args.terminology)]
        if args.profile:
            inputs.append(Path(args.profile))
        if any(p.suffix.lower() != '.json' for p in inputs):
            raise ValueError('Terminology check supports strict JSON only')
        if args.output and Path(args.output).resolve() in {p.resolve() for p in inputs}:
            raise ValueError('Refusing to overwrite an input file')
        before = {str(p): sha(p) for p in inputs}
        result = check(load(inputs[0]), load(inputs[1]), load(inputs[2]), load(args.profile) if args.profile else None, args.application)
        if any(sha(p) != before[str(p)] for p in inputs):
            raise ValueError('An input changed during the check; rerun against a stable pair')
        result['inputs'] = [{'file': str(p), 'sha256': before[str(p)]} for p in inputs]
        exit_code = 1 if result['status'] in {'failed', 'needs-review', 'incomplete-input-pair'} else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'invalid-input', 'message': str(error)}, ensure_ascii=False))
        return 2
    if args.output:
        try:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        except OSError as error:
            print(json.dumps({'status': 'invalid-output', 'message': str(error)}, ensure_ascii=False))
            return 2
    print(json.dumps({k: result[k] for k in ('status', 'application', 'counts', 'findingsByCode')} if args.output else result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
