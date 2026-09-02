from __future__ import annotations
import argparse, json, urllib.request

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('--url',default='http://127.0.0.1:8000/api/health/ready'); args=parser.parse_args()
    with urllib.request.urlopen(args.url, timeout=5) as response:
        data=json.load(response)
    print(json.dumps(data,ensure_ascii=False)); return 0 if data.get('status')=='ready' else 1
if __name__=='__main__': raise SystemExit(main())
