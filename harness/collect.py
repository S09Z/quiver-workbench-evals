#!/usr/bin/env python3
"""
collect — เก็บ snapshot ราคาจริงจาก Shopee/Lazada มาทำ fixture

ตาม MODEL_EVAL.md §17 ข้อมูลจริงคือคอขวด ไม่ใช่ตัว runner
สคริปต์นี้ทำสองอย่างแยกกันชัด ๆ:

    collect  เปิดหน้าค้นหาสาธารณะด้วยเบราว์เซอร์จริง แล้วเซฟ JSON ดิบไว้
    fixture  แปลง JSON ดิบเป็นตาราง markdown ตามรูปแบบที่เคสใน suites/ ใช้

ติดตั้ง:
    poetry install
    python -m playwright install chromium

ใช้งาน:
    python harness/collect.py collect lazada "อาหารแมว"
    python harness/collect.py collect shopee "อาหารแมว Me-O" --pages 2
    python harness/collect.py fixture results/snapshots/<ไฟล์>.json --top 10

ขอบเขตที่ตั้งใจไว้ — อ่านก่อนแก้:
- เปิดเฉพาะหน้าค้นหาสาธารณะ เท่าที่ robots.txt อนุญาต เช็คทุกครั้งก่อนยิง
- ใช้ Chromium จริงตามที่ playwright ติดตั้งมา ไม่ปลอม user-agent ไม่หมุน proxy
- ถ้าเจอหน้า captcha/punish ให้หยุดแล้วรายงาน ไม่ต้องหาทางผ่าน
- ยิงทีละหน้า เว้นระยะตาม --delay เสมอ
"""

import argparse
import json
import re
import sys
import time
import urllib.robotparser
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = ROOT / "results" / "snapshots"

DEFAULT_DELAY = 5.0       # วินาที ระหว่างหน้า อย่าลดลงโดยไม่มีเหตุผล
PAGE_TIMEOUT = 60_000
SETTLE_MS = 8_000         # รอ js เรนเดอร์การ์ดสินค้าให้ครบ

# Shopee เรนเดอร์การ์ดเฉพาะที่เข้ามาในจอ ถ้าไม่เลื่อนจะได้ข้อมูลแค่แถวบน ๆ
SCROLL_STEPS = 12
SCROLL_PAUSE_MS = 700

# เจอคำพวกนี้ในหน้า = โดนกำแพงบอท ให้หยุดทันที
BLOCK_MARKERS = ("_____tmd_____", "x5secdata", "punish", "/verify/traffic")


# ---------------------------------------------------------------------------
# แต่ละแพลตฟอร์ม: url ค้นหา + js ที่ดึงข้อมูลออกจากการ์ด
#
# หลักการเลือก selector: ยึด attribute ที่มีความหมาย (aria-label, data-*, title)
# อย่ายึด class เพราะทั้งสองเว็บใช้ class ที่ hash แล้วเปลี่ยนบ่อย
# ---------------------------------------------------------------------------

LAZADA_JS = r"""
() => {
  const num = (s) => {
    if (!s) return null;
    const m = String(s).replace(/,/g, "").match(/[\d.]+/);
    return m ? parseFloat(m[0]) : null;
  };
  return [...document.querySelectorAll("[data-qa-locator='product-item']")].map((c) => {
    const text = c.innerText || "";
    const link = c.querySelector("a[href*='/products/']");
    const href = link ? link.getAttribute("href") : null;
    // ราคาอยู่ใน span/del ที่ขึ้นต้นด้วย ฿ — กัน badge ("Subsidized ฿2.00") ออก
    const prices = [...c.querySelectorAll("span, del")]
      .filter((e) => /^฿\s?[\d,]/.test(e.textContent.trim()))
      .filter((e) => !String(e.className).includes("ic-dynamic-badge"))
      .map((e) => e.textContent.trim());
    const sold = text.match(/([\d.,]+\s?[KMkm]?)\s*(sold|ขายแล้ว|ชิ้น)/);
    const reviews = text.match(/\((\d[\d,]*)\)/);
    const loc = c.querySelector("span[title]");
    return {
      item_id: c.getAttribute("data-item-id"),
      name: (c.querySelector("a[title]") || {}).title || null,
      url: href ? (href.startsWith("//") ? "https:" + href : href) : null,
      price: num(prices[0]),
      original_price: prices.length > 1 ? num(prices[1]) : null,
      rating: null,                       // grid ของ Lazada ไม่ให้คะแนนดาวเป็นตัวเลข
      review_count: reviews ? parseInt(reviews[1].replace(/,/g, ""), 10) : null,
      sold_raw: sold ? sold[1].trim() : null,
      location: loc ? loc.getAttribute("title") : null,
    };
  });
}
"""

SHOPEE_JS = r"""
() => {
  const num = (s) => {
    if (!s) return null;
    const m = String(s).replace(/,/g, "").match(/[\d.]+/);
    return m ? parseFloat(m[0]) : null;
  };
  return [...document.querySelectorAll("[data-sqe='item']")].map((c) => {
    const text = c.innerText || "";
    const card = c.querySelector('[aria-label^="Product card:"]');
    const link = c.querySelector("a[href*='-i.']");
    const href = link ? link.getAttribute("href") : "";
    const ids = href.match(/-i\.(\d+)\.(\d+)/);
    const promo = c.querySelector('[aria-label="promotion price"]');
    const struck = c.querySelector(".line-through");
    const star = c.querySelector('img[alt="rating-star"]');
    const locEl = c.querySelector('[aria-label^="location-"]');
    const sold = text.match(/([\d.,]+\s?[KMkm]?)\s*(ขายแล้ว|sold|ชิ้น)/);
    return {
      item_id: ids ? ids[2] : null,
      shop_id: ids ? ids[1] : null,
      name: card ? card.getAttribute("aria-label").replace(/^Product card:\s*/, "") : null,
      url: href ? "https://shopee.co.th" + href.split("?")[0] : null,
      price: promo && promo.parentElement ? num(promo.parentElement.innerText) : null,
      original_price: struck ? num(struck.innerText) : null,
      rating: star && star.nextElementSibling ? num(star.nextElementSibling.innerText) : null,
      review_count: null,                 // grid ของ Shopee ให้แค่ดาว ไม่ให้จำนวนรีวิว
      sold_raw: sold ? sold[1].trim() : null,
      location: locEl ? locEl.getAttribute("aria-label").replace(/^location-/, "") : null,
    };
  });
}
"""

# ตรวจกับหน้าจริงเมื่อ 2026-09-09 — สองเว็บให้ข้อมูลคนละชุด ไม่ใช่บั๊กของ selector
# Lazada: การ์ดมีราคาเดียว ไม่มีราคาขีดฆ่า และไม่โชว์คะแนนดาวเป็นตัวเลข
# Shopee: การ์ดมีดาวและราคาก่อนลด แต่ไม่โชว์ยอดขายกับจำนวนรีวิว
MISSING_BY_PLATFORM = {
    "lazada": "Lazada ไม่ให้คะแนนดาวและราคาก่อนลดบนการ์ด (ให้ยอดขายกับจำนวนรีวิว)",
    "shopee": "Shopee ไม่ให้ยอดขายและจำนวนรีวิวบนการ์ด (ให้ดาวกับราคาก่อนลด)",
}

PLATFORMS = {
    "lazada": {
        "url": lambda q, page: f"https://www.lazada.co.th/catalog/?q={quote(q)}&page={page}",
        "cards": "[data-qa-locator='product-item']",
        "js": LAZADA_JS,
    },
    "shopee": {
        "url": lambda q, page: f"https://shopee.co.th/search?keyword={quote(q)}&page={page - 1}",
        "cards": "[data-sqe='item']",
        "js": SHOPEE_JS,
    },
}


def check_robots(url: str) -> None:
    """robots.txt ไม่อนุญาต = จบ ไม่ต้องหาทางอ้อม

    เช็คทั้งกลุ่ม "*" และกลุ่ม Googlebot แล้วเอาอันที่เข้มกว่า
    เพราะ robots.txt ของ Shopee ประกาศแค่กลุ่ม Googlebot/Bingbot ไม่มีกลุ่ม "*" เลย
    ตาม RFC 9309 แปลว่า bot ทั่วไปไม่โดนกฎอะไรเลย ซึ่งเปิดกว้างกว่าที่เว็บตั้งใจไว้ชัด ๆ
    เลยยึดกฎที่เข้มที่สุดที่เขาประกาศไว้แทน
    """
    parts = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        rp.read()
    except Exception as e:
        sys.exit(f"อ่าน robots.txt ของ {parts.netloc} ไม่ได้ ({e}) — หยุดไว้ก่อน")
    for ua in ("*", "Googlebot"):
        if not rp.can_fetch(ua, url):
            sys.exit(
                f"robots.txt ของ {parts.netloc} ไม่อนุญาต path นี้ (กฎของ {ua}):\n  {url}"
            )


def scroll_through(page) -> None:
    """เลื่อนจนสุดหน้าเพื่อบังคับให้การ์ดที่ lazy-render โผล่ครบก่อนดึงข้อมูล"""
    for i in range(1, SCROLL_STEPS + 1):
        page.evaluate("(f) => window.scrollTo(0, document.body.scrollHeight * f)", i / SCROLL_STEPS)
        page.wait_for_timeout(SCROLL_PAUSE_MS)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(SCROLL_PAUSE_MS)


def parse_sold(raw):
    """'8.8K' -> 8800 ; '1.2พัน' ไม่รองรับ คืน None ให้เห็นชัดว่าอ่านไม่ออก"""
    if not raw:
        return None
    m = re.match(r"([\d.,]+)\s?([KMkm]?)", raw.strip())
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return int(n * {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1))


def collect(platform: str, query: str, pages: int, delay: float, headed: bool) -> Path:
    from playwright.sync_api import sync_playwright

    conf = PLATFORMS[platform]
    items, seen = [], set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page(locale="th-TH")
        for n in range(1, pages + 1):
            url = conf["url"](query, n)
            check_robots(url)
            if n > 1:
                time.sleep(delay)
            print(f"  หน้า {n}: {url}", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            page.wait_for_timeout(SETTLE_MS)
            scroll_through(page)

            landed = page.url
            if any(m in landed for m in BLOCK_MARKERS):
                browser.close()
                sys.exit(
                    f"โดนกำแพงบอทของ {platform} (redirect ไป {landed[:80]}...)\n"
                    "ไม่ได้ออกแบบให้ผ่านด่านนี้ — ลองใหม่ทีหลัง หรือ --headed แล้วดูด้วยตา"
                )
            found = page.locator(conf["cards"]).count()
            if not found:
                print(f"  ! หน้า {n} ไม่เจอการ์ดสินค้าเลย — โครงหน้าเว็บอาจเปลี่ยน", file=sys.stderr)
            for row in page.evaluate(conf["js"]):
                if not row.get("name"):
                    continue                # การ์ดโฆษณา/ช่องว่างที่ยังไม่เรนเดอร์
                key = row.get("item_id") or row.get("url")
                if key in seen:
                    continue
                seen.add(key)
                row["sold"] = parse_sold(row.pop("sold_raw", None))
                row["page"] = n
                items.append(row)
            print(f"    เจอ {found} การ์ด สะสม {len(items)} รายการ", file=sys.stderr)
        browser.close()

    slug = re.sub(r"[^\w฀-๿]+", "-", query).strip("-")[:40]
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOTS_DIR / f"{date.today().isoformat()}__{platform}__{slug}.json"
    out.write_text(
        json.dumps(
            {
                "platform": platform,
                "query": query,
                "collected_at": date.today().isoformat(),
                "pages": pages,
                "count": len(items),
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out


def render_fixture(snapshot: Path, top: int) -> str:
    snapshot = snapshot.resolve()
    d = json.loads(snapshot.read_text(encoding="utf-8"))
    items = [i for i in d["items"] if i.get("price")][:top]

    lines = [
        f"**คำค้น:** {d['query']} — {d['platform']}",
        f"**วันที่เก็บข้อมูล:** {d['collected_at']} "
        f"(ราคา ณ ขณะเก็บ จากหน้าค้นหาสาธารณะ {d['count']} รายการ แสดง {len(items)} รายการแรก)",
        "",
        "| # | ชื่อสินค้า | ราคา (บาท) | ราคาก่อนลด | ขายแล้ว | ดาว | รีวิว | จังหวัด |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n, i in enumerate(items, 1):
        def cell(v, fmt="{}"):
            return "—" if v in (None, "") else fmt.format(v)

        name = (i.get("name") or "").replace("|", "/")[:70]
        lines.append(
            f"| {n} | {name} "
            f"| {i['price']:,.0f} "
            f"| {cell(i.get('original_price'), '{:,.0f}')} "
            f"| {cell(i.get('sold'), '{:,}')} "
            f"| {cell(i.get('rating'))} "
            f"| {cell(i.get('review_count'), '{:,}')} "
            f"| {cell(i.get('location'))} |"
        )
    lines += [
        "",
        "**ข้อจำกัดของข้อมูลชุดนี้ (บอกไว้ตรง ๆ):**",
        f"- ช่องที่เป็น — คือแพลตฟอร์มไม่ได้แสดงค่านั้นบนหน้าค้นหา ไม่ใช่ว่าค่าเป็นศูนย์: {MISSING_BY_PLATFORM[d['platform']]}",
        f"- เก็บจากหน้าค้นหาคำว่า \"{d['query']}\" อย่างเดียว ไม่ใช่ทั้งตลาด "
        "ลำดับที่เห็นคือลำดับที่แพลตฟอร์มจัดให้ ซึ่งมีโฆษณาและ personalization ปนอยู่",
        "- ราคาเป็นราคาที่แสดงบนการ์ด ยังไม่รวมค่าส่งและคูปองที่ต้องกดเก็บเอง",
        "- ขนาดบรรจุไม่ได้แยกออกมาเป็นคอลัมน์ ต้องอ่านจากชื่อสินค้าเอง "
        "ถ้าจะเทียบราคาต่อกิโล ต้องกรอกขนาดด้วยมือก่อน",
        f"- ที่มา: `{snapshot.relative_to(ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="เก็บ snapshot จากหน้าค้นหา")
    c.add_argument("platform", choices=sorted(PLATFORMS))
    c.add_argument("query")
    c.add_argument("--pages", type=int, default=1)
    c.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    c.add_argument("--headed", action="store_true", help="เปิดเบราว์เซอร์ให้เห็น เวลา debug")

    f = sub.add_parser("fixture", help="แปลง snapshot เป็นตาราง markdown")
    f.add_argument("snapshot", type=Path)
    f.add_argument("--top", type=int, default=15)

    a = ap.parse_args()
    if a.cmd == "collect":
        out = collect(a.platform, a.query, a.pages, a.delay, a.headed)
        print(out)
    else:
        sys.stdout.write(render_fixture(a.snapshot, a.top))


if __name__ == "__main__":
    main()
