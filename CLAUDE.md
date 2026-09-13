
# quiver-workbench-evals

สนามซ้อมส่วนตัวสำหรับทดสอบว่าโมเดลไหนใช้ทำงานจริงของเราได้ดีแค่ไหน

ไม่ผูกกับโดเมนไหน แต่ละโดเมนคือหนึ่ง suite ใต้ `suites/`
ชุดแรกคือ `catfood` (วิเคราะห์ตลาด niche เชิงเศรษฐศาสตร์พฤติกรรม)
แต่ harness ออกแบบให้ใช้กับอะไรก็ได้

เจ้าของโปรเจกต์เป็น web developer มีพื้นฐาน ML/DL/Python ระดับใช้งานได้
**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.


## เป้าหมาย

ไม่ใช่การหาโมเดลที่ "สอบผ่าน" แต่คือการมี baseline ไว้เทียบทุกครั้งที่
โมเดลรุ่นใหม่ออก ที่มาของแนวคิดคือวิธีทำงานของ Tobi Lütke — เวลา AI ทำงาน
ที่สั่งได้ไม่ดี นั่นคือ eval สำหรับ AI ตัวถัดไป เป็นการสะสมกระบอกลูกธนู
ของเทสต์ไว้เรื่อย ๆ (quiver = กระบอกลูกธนู ที่มาของชื่อ repo)

## โครงสร้าง

```
harness/run.py            ตัว runner ใช้ร่วมกันทุก suite
suites/<ชื่อ>/
    SUITE.md              เอกสารอธิบายเคสและเกณฑ์ให้คะแนน
    cases/*.json          โจทย์ + rubric
    fixtures/             ข้อมูลจริง อ้างจากเคสด้วย {{ชื่อไฟล์}}
    models.json           (ไม่บังคับ) ทับลิสต์โมเดลเฉพาะชุดนี้
results/                  คำตอบดิบ + scores.json ที่กรอกด้วยมือ
scratch/                  ที่ลองอะไรเล่น ๆ ไม่ต้องเป็นระเบียบ ไม่เข้า git
```

`scratch/` มีไว้ให้ทดลองได้อิสระโดยไม่ต้องรู้สึกว่าต้องทำให้เรียบร้อยก่อน
ถ้าอะไรใน scratch เริ่มมีประโยชน์ซ้ำ ๆ ค่อยย้ายมาเป็น suite

## คำสั่ง

```bash
python harness/run.py init <suite>            สร้างชุดใหม่
python harness/run.py run <suite>             รันทุกเคส ทุกโมเดล
python harness/run.py run <suite> --cases e03
python harness/run.py run <suite> --repeat 3  วัด self-consistency
python harness/run.py report [--suite X]      สรุปคะแนน
```

ต้องมี `OPENROUTER_API_KEY` ใน `.env`
ลิสต์ `DEFAULT_MODELS` อยู่ต้นไฟล์ `run.py` — เช็ค model id ปัจจุบันที่
openrouter.ai/models ก่อนรัน เพราะชื่อรุ่นเปลี่ยนบ่อย

## หลักการออกแบบเคส (ใช้กับทุก suite)

งานวิเคราะห์ไม่มีเฉลยตายตัว จึงต้องแปลงให้ตรวจได้ด้วย 4 กลไก

| กลไก | ทำยังไง |
|---|---|
| Verifiable | บังคับให้อ้างแหล่ง แล้วไล่เปิดเช็คทีละอัน |
| Holdout | เรารู้คำตอบอยู่แล้วแต่ปิดไว้ ให้โมเดลทาย แล้วเทียบ |
| Computable | โจทย์ที่มีเลขคำนวณตามได้ ผิดคือผิด |
| Trap | โจทย์ที่คำตอบซึ่งฟังดูดีคือคำตอบผิด ใช้จับ pattern-matching |

สเกลคะแนนต่อเกณฑ์: 0 = ไม่มี/ผิด, 1 = ตื้นหรือคลุมเครือ, 2 = ถูกและใช้ได้จริง

Failure mode ที่ควรมีเคสจับไว้ในทุก suite: **sycophancy** (ใส่ข้ออ้างปลอม
ลงไปดูว่าโมเดลค้านไหม) และ **การมั่วตัวเลขพร้อมแหล่งอ้างอิงที่ไม่มีอยู่จริง**

## การตัดสินใจที่ตกลงกันไว้แล้ว — อย่าเปลี่ยนโดยไม่คุยก่อน

**ให้คะแนนด้วยมือในช่วงแรก** ยังไม่ทำ LLM-as-judge จนกว่าจะอ่านคำตอบเอง
ครบ 30-40 อัน เพราะยังไม่รู้ว่า "คำตอบที่ดี" ในโดเมนนี้หน้าตายังไง

**ยังไม่ fine-tune** ลำดับคือ context engineering → eval → ปรับ prompt
และบริบท → แล้วค่อยคิดเรื่อง distillation ตอนมีงานแคบ ๆ ที่รันซ้ำเยอะจริง
เคส Shopify ที่เป็นแรงบันดาลใจรันที่ 72 ล้านชิ้นต่อวัน คนละสเกลกัน

**เก็บคำตอบดิบไว้เสมอ** ห้ามลบ ต้องย้อนดูได้ว่าโมเดลรุ่นเก่าตอบอะไร

**commit `scores.json` เข้า git** คะแนนคือของมีค่าที่สุดที่สะสมได้
ส่วนคำตอบดิบไฟล์ใหญ่ เก็บไว้ในเครื่องพอ

## สถานะ

- [x] harness รองรับหลาย suite เทสต์แล้วว่ารันได้
- [ ] suite `catfood` — ใส่เคส E01-E10 จาก EVALS.md เดิม
- [x] scraper Shopee/Lazada — `harness/collect.py` เก็บหน้าค้นหาได้ทั้งสองเว็บ
      (ยังเป็นระดับ search grid เท่านั้น ยังไม่เข้าหน้าสินค้า/หน้าร้าน)
- [ ] fixtures จริง และ baseline run ครั้งแรก

เคสที่ใช้ข้อมูลจริงซึ่งโมเดลไม่เคยเห็นจะให้สัญญาณดีที่สุด
เพราะฉะนั้นการเก็บข้อมูลคือคอขวด ไม่ใช่ตัว harness

## แนวทางขยาย

กฎเดียว: ทุกครั้งที่โมเดลทำงานจริงพัง ให้แปลงเป็นเคสใหม่ทันทีก่อนจะลืมว่า
มันพังยังไง ตั้งเป้าว่าภายใน 2 เดือน อย่างน้อยครึ่งหนึ่งของเคสควรเป็นของที่
เจอมาเอง ไม่ใช่ของที่ร่างไว้ตั้งแต่ต้น
