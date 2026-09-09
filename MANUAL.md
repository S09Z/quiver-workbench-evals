# MANUAL — คู่มือใช้งาน quiver-workbench-evals

คู่มือปฏิบัติงาน (how-to) แยกจาก [CLAUDE.md](CLAUDE.md) ที่เป็นหลักการ/ปรัชญาของโปรเจกต์
และ [MODEL_EVAL.md](MODEL_EVAL.md) ที่เป็นมาตรฐานการออกแบบเคส — ไฟล์นี้บอกแค่ "ต้องรันคำสั่งอะไร"

## 1. ติดตั้งครั้งแรก

```bash
poetry install
python -m playwright install chromium   # เฉพาะตอนจะเก็บข้อมูลจาก Shopee/Lazada ด้วย collect.py
cp .env.example .env                    # แล้วใส่ OPENROUTER_API_KEY จริงของคุณ
```

ตรวจว่าติดตั้งถูกต้อง:

```bash
poetry run python harness/run.py --help
```

## 2. โครงสร้างที่ต้องรู้

```
harness/run.py         ตัว runner ยิง prompt ไปหลายโมเดล ใช้ร่วมกันทุก suite
harness/collect.py     ตัวเก็บ snapshot ราคาจริงจาก Shopee/Lazada (ดูข้อ 4)
suites/<ชื่อ>/
    SUITE.md            เอกสารอธิบายเคสของ suite นั้น
    cases/*.json        โจทย์ + rubric — {id, title, temperature, fixtures, prompt, rubric}
    fixtures/*.md       ข้อมูลจริง อ้างจาก case ด้วย {{ชื่อไฟล์}}
    models.json         (ไม่บังคับ) ทับ DEFAULT_MODELS เฉพาะ suite นี้
results/                คำตอบดิบจากการรัน + scores.json (คำตอบดิบไม่เข้า git ตาม .gitignore)
results/snapshots/      JSON ดิบจาก collect.py (ไม่เข้า git)
scratch/                ที่ลองอะไรเล่น ๆ ไม่เข้า git
```

## 3. รัน eval (harness/run.py)

```bash
# รันทุกเคสในชุด catfood ด้วยโมเดล default
poetry run python harness/run.py run catfood

# รันเฉพาะบางเคส
poetry run python harness/run.py run catfood --cases e01 e02

# รันซ้ำ 3 รอบ (วัด self-consistency — ใช้กับ e03/e06 ตามที่ SUITE.md แนะนำ)
poetry run python harness/run.py run catfood --cases e03 e06 --repeat 3

# ทับโมเดลชั่วคราว ไม่ต้องแก้ไฟล์
poetry run python harness/run.py run catfood --models anthropic/claude-opus-5

# รันทับของเดิม (ปกติจะ skip เคสที่มีไฟล์คำตอบอยู่แล้ว กันจ่ายเงินซ้ำ)
poetry run python harness/run.py run catfood --force
```

ผลลัพธ์ไปอยู่ที่ `results/<วันที่>__catfood__<โมเดล>/<case>__r<รอบ>.md` พร้อม `.meta.json`
(token/เวลา) และ `scores.json` ที่ถูกสร้างเป็นฟอร์มเปล่าให้กรอกเอง

**สร้าง suite ใหม่:**

```bash
poetry run python harness/run.py init <ชื่อ-suite>
```

จะได้ `suites/<ชื่อ>/SUITE.md` และ `cases/e01.json` ตัวอย่าง — นี่คือ schema ตัวจริงที่ harness
อ่าน (`id/title/temperature/fixtures/prompt/rubric`) อย่าสร้าง case ตาม schema อื่น

**ดูสรุปคะแนน:**

```bash
poetry run python harness/run.py report                # ทุก suite
poetry run python harness/run.py report --suite catfood
```

ต้องกรอก `scores.json` เองก่อนถึงจะมีอะไรให้สรุป (ดูข้อ 6)

## 4. เก็บข้อมูลจริงมาทำ fixture (harness/collect.py)

สองขั้นตอนแยกกันชัด ๆ — `collect` ดึงข้อมูลดิบ, `fixture` แปลงเป็นตารางที่เอาไปวางใน case ได้เลย

```bash
# ขั้น 1: เก็บ snapshot จากหน้าค้นหาสาธารณะ (เคารพ robots.txt เสมอ)
poetry run python harness/collect.py collect shopee "อาหารแมว Me-O" --pages 2
poetry run python harness/collect.py collect lazada "อาหารแมว Me-O"

# ขั้น 2: แปลงเป็นตาราง markdown (ตรวจด้วยตาก่อนเซฟ!)
poetry run python harness/collect.py fixture results/snapshots/<ไฟล์ที่ได้>.json --top 15
```

`fixture` พ่นตาราง markdown ออกทาง stdout — **อ่านตรวจก่อนเสมอ** แล้วค่อย copy ไปวางเป็นไฟล์ใน
`suites/<ชื่อ>/fixtures/` เอง (สคริปต์ไม่เขียนทับไฟล์ fixture ให้อัตโนมัติ ตั้งใจให้มีคนอ่านคั่นกลาง)

ข้อจำกัดที่ต้องรู้ (ไม่ใช่บั๊ก ตรวจกับหน้าจริงแล้ว):
- **Shopee**: ให้ดาว+ราคาก่อนลด แต่ไม่ให้ยอดขาย/จำนวนรีวิวบนหน้าค้นหา
- **Lazada**: ให้ยอดขาย+จำนวนรีวิว แต่ไม่ให้ดาว/ราคาก่อนลด
- ถ้าต้องการครบทุกช่อง ต้องเก็บทั้งสองเว็บแล้วจับคู่เอง หรือเข้าหน้าสินค้าทีละตัว (ยังไม่ได้ทำ)
- ขนาดบรรจุไม่ได้แยกคอลัมน์ ต้องอ่านจากชื่อสินค้าเอง ถ้าจะเทียบราคา/กิโลต้องกรอกเองก่อน
- เจอกำแพงบอท/captcha → สคริปต์หยุดแล้วบอกตรง ๆ ไม่พยายามหาทางผ่าน (ตั้งใจ)

## 5. เขียน case ใหม่

Case คือไฟล์ JSON หน้าตาแบบนี้:

```json
{
  "id": "e01",
  "title": "ชื่อสั้น ๆ อธิบายว่าเคสนี้ทดสอบอะไร",
  "temperature": 1.0,
  "fixtures": ["e01-data.md"],
  "prompt": "...ใช้ {{e01-data.md}} เพื่อดึงเนื้อไฟล์ fixture มาแทรกในนี้...",
  "rubric": [
    "เกณฑ์ข้อ 1 เขียนให้ตรวจได้จริง ไม่ใช่ 'คำตอบดี' (0-2)",
    "ธงแดง: ถ้าเจอ X ให้ 0 ทันที"
  ]
}
```

**สำคัญ — ไฟล์ fixture ที่ไม่อยาก(ห้าม)ให้โมเดลเห็น** (เช่น เฉลยของเคส holdout อย่าง E05):
**อย่าใส่ชื่อไฟล์นั้นใน `"fixtures"` ของ case** — harness แทรกเฉพาะไฟล์ที่ประกาศไว้ในลิสต์นี้เท่านั้น
ตัวอย่างจริงในโปรเจกต์: `suites/catfood/cases/e05.json` อ้างแค่ `e05-shop1.md` (ให้โมเดลเห็น)
ส่วน `e05-shop1-answer.md` (เฉลย) ไม่ถูกอ้างที่ไหนเลย จึงไม่มีทางหลุดเข้า prompt

**ข้อมูลที่เป็น mockup/สมมติ (ไม่ใช่ข้อมูลจริง):** ให้บอกในตัว fixture ที่โมเดลเห็นด้วยว่า
"ข้อมูลสมมติ" ตรง ๆ (โมเดลควรรู้ว่านี่ไม่ใช่ตลาดจริง) แต่รายละเอียดที่มาของการเดา/เทียบกับข้อมูล
จริงที่ตรวจสอบแล้ว ให้แยกไว้อีกไฟล์ที่ไม่อยู่ใน `fixtures` (ดูตัวอย่าง
`e09-gager-lineup-prices.md` คู่กับ `e09-gager-lineup-notes.md`)

## 6. ให้คะแนน

**ให้คะแนนด้วยมือ** — ยังไม่ทำ LLM-as-judge จนกว่าจะอ่านคำตอบเองครบ 30–40 อัน (การตัดสินใจที่
ตกลงกันไว้แล้ว ดู CLAUDE.md) เปิด `results/<run>/e01__r1.md` อ่านคำตอบดิบ แล้วกรอกคะแนนใน
`results/<run>/scores.json` ตามเกณฑ์ 0/1/2 ที่เขียนไว้ใน rubric ของ case นั้น

```json
{
  "e01__r1": {
    "criteria": {
      "ตรวจด้วยมือ: เปิด URL ทุกอันจริง...": 2,
      "ตัวเลขในคำตอบตรงกับตัวเลขในแหล่งจริง (0-2)": 1
    },
    "notes": "อธิบายว่าทำไมให้คะแนนนี้ โดยเฉพาะถ้าให้ 0"
  }
}
```

`scores.json` **ต้อง commit เข้า git** — เป็นของมีค่าที่สุดที่สะสมได้ (คำตอบดิบไฟล์ใหญ่เก็บไว้ใน
เครื่องพอ ไม่ต้อง commit)

## 7. สถานะปัจจุบันของ suite `catfood`

รันได้จริง 12 เคส: `e01`–`e08`, `e02-en`/`e03-en`/`e06-en` (คู่เทียบภาษา), `e09-gager-lineup`
รายละเอียดแต่ละเคสดูที่ [suites/catfood/SUITE.md](suites/catfood/SUITE.md)

**ค้างอยู่ก่อนรันจริงได้เต็มรูปแบบ:**
- `e06`/`e06-en` มี `[FILL IN]` รอข้อสังเกตตลาดจริง 3 ข้อจากคุณ
- `e07` มี `[FILL IN]` รอเลข unique visitor/สัปดาห์ และ conversion rate จริง
- `e05` มีแค่ shop1 (จาก Shopee, SmartHeart & Me-O Official) — ต้องเก็บ shop2/shop3 เพิ่มก่อน
  จะเชื่อผลได้ (ร้านเดียวคือการโยนเหรียญ)
- `e09-gager-lineup` ใช้ข้อมูล **mockup** ล้วน ๆ (ราคาที่ผู้ใช้ให้มาไม่ตรงกับราคาจริงบน Shopee ที่
  ตรวจสอบแล้ว) — ดูรายละเอียดใน `fixtures/e09-gager-lineup-notes.md`

**ยังไม่ได้ทำ:**
- Phase 4: ตรวจ `DEFAULT_MODELS` ใน `harness/run.py` กับ openrouter.ai/models จริงก่อนรัน
  (model id ในโค้ดตอนนี้เป็น placeholder)
- Phase 5: baseline run จริง (ต้องมี `OPENROUTER_API_KEY` และใช้เงินจริง)
- Phase 6: ให้คะแนนด้วยมือ
