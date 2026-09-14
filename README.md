# quiver-workbench-evals

สนามซ้อมส่วนตัวสำหรับทดสอบว่าโมเดลไหนใช้ทำงานจริงของเราได้ดีแค่ไหน

ดูรายละเอียดใน [CLAUDE.md](CLAUDE.md)

## ติดตั้ง

```bash
poetry install
python -m playwright install chromium   # เฉพาะตอนจะเก็บข้อมูลจาก Shopee/Lazada
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

## ใช้งาน

```bash
python harness/run.py init <suite>
python harness/run.py run <suite>
python harness/run.py report
```

## เก็บข้อมูลตลาดมาทำ fixture

```bash
python harness/collect.py collect lazada "อาหารแมว Me-O"      # เซฟ JSON ดิบ
python harness/collect.py collect shopee "อาหารแมว Me-O" --pages 2
python harness/collect.py fixture results/snapshots/<ไฟล์>.json --top 15
```

`collect` เปิดหน้าค้นหาสาธารณะด้วย Chromium จริง เช็ค robots.txt ก่อนยิงทุกครั้ง
และเว้นระยะระหว่างหน้า ถ้าเจอหน้า captcha จะหยุดแล้วบอกตรง ๆ ไม่พยายามผ่านด่าน
JSON ดิบเก็บไว้ใน `results/snapshots/` (ไม่เข้า git) ส่วนตาราง markdown ที่ `fixture`
พ่นออกมาให้ตรวจด้วยตาก่อนแล้วค่อยเซฟลง `suites/<ชื่อ>/fixtures/`

สองแพลตฟอร์มให้ข้อมูลคนละชุด (ตรวจกับหน้าจริงแล้ว ไม่ใช่บั๊ก):

| | ราคา | ราคาก่อนลด | ยอดขาย | ดาว | จำนวนรีวิว | จังหวัด |
|---|---|---|---|---|---|---|
| Lazada | ✓ | — | ✓ | — | ✓ | ✓ |
| Shopee | ✓ | ✓ | — | ✓ | — | ✓ |

ถ้าต้องการครบทุกช่อง ต้องเก็บทั้งสองเว็บแล้วจับคู่เอง — หรือเข้าหน้าสินค้าทีละตัว
ซึ่งยังไม่ได้ทำในตอนนี้
