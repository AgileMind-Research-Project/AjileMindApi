import asyncio, os, sys, re
sys.path.insert(0, "d:/Research/AjileMindApi")
from dotenv import load_dotenv
load_dotenv("d:/Research/AjileMindApi/.env")
import aiomysql

TASK_RE = re.compile(
    r"(.+?)\s*\(TAM-(\d+)\)\s*[\u2012\u2013\u2014\u2212\-\s:]*\s*(\d+(?:\.\d+)?)\s*(h(?:ours?)?|SP|story\s*points?)",
    re.IGNORECASE,
)

async def main():
    conn = await aiomysql.connect(
        host=os.getenv("DB_HOST", "hopper.proxy.rlwy.net"),
        port=int(os.getenv("DB_PORT", "46189")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        db="sliit", charset="utf8mb4"
    )
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute(
            "SELECT id, meeting_id, title, created_at, "
            "LENGTH(transcript_content) as tlen, transcript_content "
            "FROM transcripts ORDER BY created_at DESC LIMIT 10"
        )
        rows = await cur.fetchall()
    conn.close()

    if not rows:
        print("NO TRANSCRIPTS FOUND")
        return

    for r in rows:
        content = r["transcript_content"] or ""
        has_tam = "TAM-" in content.upper()
        matches = TASK_RE.findall(content)
        print("----")
        print("ID:", r["id"], "| meeting_id:", r["meeting_id"],
              "| len:", r["tlen"], "| has_TAM:", has_tam,
              "| regex_matches:", len(matches))
        print("title:", r["title"])
        print("preview:", repr(content[:300]))
        if has_tam:
            print("TAM lines:")
            for ln in content.splitlines():
                if "TAM-" in ln.upper():
                    print("  LINE:", repr(ln))
        print()

asyncio.run(main())


from dotenv import load_dotenv
load_dotenv('d:/Research/AjileMindApi/.env')

import aiomysql

TASK_RE = re.compile(
    r'(.+?)\s*\(TAM-(\d+)\)\s*'
    r'[\u2012\u2013\u2014\u2212\-\s:]*\s*'
    r'(\d+(?:\.\d+)?)\s*(h(?:ours?)?|SP|story\s*points?)',
    re.IGNORECASE,
)

async def main():
    host = os.getenv('DB_HOST', 'hopper.proxy.rlwy.net')
    port = int(os.getenv('DB_PORT', '46189'))
    user = os.getenv('DB_USER', 'root')
    pwd  = os.getenv('DB_PASSWORD', '')

    print("Connecting to", host, port)
    conn = await aiomysql.connect(
        host=host, port=port, user=user, password=pwd,
        db='sliit', charset='utf8mb4'
    )

    async with conn.cursor(aiomysql.DictCursor) as cur:
        # Get latest transcript
        await cur.execute(
            'SELECT id, meeting_id, created_at, '
            'LENGTH(transcript_content) as total_len, '
            'LEFT(transcript_content, 5000) as snippet '
            'FROM transcripts ORDER BY created_at DESC LIMIT 1'
        )
        row = await cur.fetchone()

    conn.close()

    if not row:
        print("NO TRANSCRIPTS FOUND IN sliit.transcripts")
        return

    print(f"\n=== Transcript ID: {row['id']} | Meeting: {row['meeting_id']} | Created: {row['created_at']}")
    print(f"=== Total length: {row['total_len']} chars\n")

    snippet = row['snippet'] or ''

    # Print first 2000 chars as repr (shows exact dash chars, line endings)
    print("--- repr(first 2000 chars) ---")
    print(repr(snippet[:2000]))

    # Show lines containing TAM-
    print("\n--- Lines containing 'TAM-' ---")
    tam_lines = [ln for ln in snippet.splitlines() if 'TAM-' in ln.upper()]
    if tam_lines:
        for ln in tam_lines:
            print(f"  {repr(ln)}")
    else:
        print("  *** NONE FOUND ***")

    # Test the parser task regex live
    print("\n--- Testing task_re regex ---")
    task_re = re.compile(
        r'(.+?)\s*\(TAM-(\d+)\)\s*'
        r'[\u2012\u2013\u2014\u2212\-\s:]*\s*'
        r'(\d+(?:\.\d+)?)\s*(h(?:ours?)?|SP|story\s*points?)',
        re.IGNORECASE,
    )
    matched = 0
    for ln in snippet.splitlines():
        m = task_re.search(ln.strip())
        if m:
            matched += 1
            print(f"  MATCH: TAM-{m.group(2)} | {m.group(1).strip()!r} | effort={m.group(3)}{m.group(4)}")
    print(f"\nTotal regex matches: {matched}")

asyncio.run(main())
