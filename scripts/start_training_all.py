import os
import sys
import time
from typing import Dict, Any, List

# Ensure repo root on path
THIS_DIR = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(THIS_DIR, '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.training import JobManager  # type: ignore
from src import user_store  # type: ignore


def list_all_users() -> List[str]:
    try:
        data = user_store._load_users()  # private but OK for internal script
        return sorted(list(data.get('users', {}).keys()))
    except Exception:
        return []


def main() -> None:
    users = list_all_users()
    if not users:
        print('[training] No users found. Register a user first, then re-run.')
        return

    jm = JobManager()
    submitted: Dict[str, str] = {}

    # Submit one job per user using their current profile
    for u in users:
        prof = user_store.load_profile(u)
        purpose = str(prof.get('purpose', '') or '')
        cfg: Dict[str, Any] = prof.get('config') if isinstance(prof.get('config'), dict) else {}
        job = jm.submit(u, purpose, cfg)
        submitted[u] = job['id']
        print(f"[training] Submitted job for user={u} id={job['id']}")

    # Track until all done/canceled/failed
    print('[training] Waiting for jobs to complete...')
    unfinished = set(submitted.values())
    spinner = ['|','/','-','\\']
    si = 0
    while unfinished:
        time.sleep(0.5)
        si = (si + 1) % len(spinner)
        for u, jid in list(submitted.items()):
            j = jm.get(u, jid)
            if not j:
                continue
            st = j.get('status')
            if st in ('done','failed','canceled'):
                if jid in unfinished:
                    unfinished.remove(jid)
                print(f"[training] {u}:{jid} -> {st}")
        # lightweight progress indicator
        sys.stdout.write(f"\r[training] running {len(unfinished)} jobs {spinner[si]}")
        sys.stdout.flush()

    print('\n[training] All jobs completed.')


if __name__ == '__main__':
    main()
