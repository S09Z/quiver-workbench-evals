# Local LLM backend — design

**วันที่:** 2026-09-09
**สถานะ:** อนุมัติดีไซน์แล้ว รอทำ implementation plan

## 1. ที่มา

รัน baseline ครั้งแรก (`run catfood`, 12 เคส × 4 โมเดล) **พังทั้ง 48 งาน** ด้วย error เดียวกันหมด:

```
Error code: 402 — This request requires more credits, or fewer max_tokens.
You requested up to 65536 tokens, but can only afford 1600.
```

สาเหตุคือเครดิต OpenRouter หมด ประกอบกับ [`harness/run.py`](../../../harness/run.py) ไม่ได้ตั้ง
`max_tokens` เลย โมเดลจึงขอเพดานของตัวเอง (65,536 tokens) แล้ว OpenRouter กันเครดิตล่วงหน้าไม่ไหว

เป้าหมายของงานนี้: **ให้รัน eval จบได้โดยไม่ต้องเติมเครดิต** โดยยิงไปที่ Ollama ที่ติดตั้งและรัน
อยู่แล้วบนเครื่อง ยอมรับว่าคุณภาพคำตอบจากโมเดล 8B จะด้อยกว่า frontier models อย่างชัดเจน —
นั่นเป็นเรื่องรอง เพราะจุดประสงค์คือปลดล็อกให้ทดสอบ harness ได้ครบวงจรก่อน

## 2. ขอบเขต

**ทำ:**
- เพิ่ม backend `ollama` (ทั้งโมเดลในเครื่องและโมเดล `:cloud` ที่ยิงผ่าน endpoint เดียวกัน)
- เลือก backend ด้วย flag `--backend` ต่อการรันหนึ่งครั้ง
- ติดป้าย backend ลงในผลลัพธ์ให้ `report` แยก lane ได้
- เช็คสภาพก่อนรัน (preflight) เพื่อไม่ให้เกิด error ซ้ำ ๆ 48 ครั้งอีก
- ตั้งเพดาน `max_tokens` พร้อมบันทึกว่าคำตอบไหนถูกตัด

**ไม่ทำ (YAGNI):**
- auto-pull โมเดลที่ยังไม่ได้โหลด และ auto-start ollama daemon
- backend สำหรับ LM Studio (ติดตั้งไว้แล้วแต่ยังไม่ได้เปิด เพิ่มทีหลังได้ด้วยการเติม 1 entry)
- streaming, per-model temperature override

## 3. ข้อเท็จจริงที่ตรวจสอบมาแล้ว (2026-09-09)

| สิ่งที่ตรวจ | ผล |
|---|---|
| เครื่อง | Apple M3, RAM 16 GB, macOS 26.6.2 |
| Ollama | ติดตั้งและรันอยู่ที่ `:11434` |
| โมเดลในเครื่อง | `qwen3:latest` (8.2B), `llama3:8b`, `deepseek-r1:latest` (8.2B) + coder models |
| Ollama กับ OpenAI SDK ที่ harness ใช้ | ใช้ได้ทันที ไม่ต้องแก้รูปแบบการเรียก API |
| ความเร็ว | `qwen3:latest` ตอบคำถาม "2+2" ใน 21.7 วิ (completion 138 tokens เพราะพ่น thinking) |
| ชื่อ tag | ต้องตรงเป๊ะ — `qwen3:8b` ไม่มีอยู่จริง ต้องเป็น `qwen3:latest` |
| `kimi-k2.5:cloud`, `qwen3-coder-next:cloud` ที่โหลดไว้ | **ถูก retire แล้วทั้งคู่** (HTTP 410) |
| cloud models ที่ยังใช้ได้ | `glm-5.3`, `kimi-k3`, `deepseek-v4-pro`, `qwen3.5:122b`, `gpt-oss:120b`, `minimax-m3` |

## 4. ทางเลือกที่พิจารณา

| แบบ | สรุป | ผลการตัดสิน |
|---|---|---|
| A. ใส่ prefix ที่ model id (`ollama/qwen3:latest`) | ปนหลาย backend ในรันเดียวได้ | ไม่เลือก |
| **B. flag `--backend` สลับทั้งรัน** | ง่ายที่สุด ไม่มีอะไรกำกวมในชื่อโมเดล | **เลือกแบบนี้** |
| C. ไฟล์ `providers.json` | ยืดหยุ่นสุด แต่ over-engineer สำหรับ 2 backend | ไม่เลือก |

ข้อแลกเปลี่ยนของ B ที่ยอมรับ: รันปน backend ในคำสั่งเดียวไม่ได้ ต้องรันสองรอบ — ชดเชยด้วยการ
ติดป้าย backend ลงในชื่อโฟลเดอร์ผลลัพธ์ (ข้อ 5.4) เพื่อให้ `report` ยังรวมเป็นตารางเดียวที่อ่านออก
ว่าแถวไหนมาจาก lane ไหน

## 5. ดีไซน์

### 5.1 ตาราง backend

แทนค่าคงที่ที่ฝังอยู่ใน `client()` ด้วย dict เดียว:

```python
BACKENDS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "workers": 4,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,      # ไม่ต้องใช้คีย์ ส่ง dummy string
        "workers": 1,
    },
}
```

`client()` รับ `backend` เป็นพารามิเตอร์แล้วคืน `OpenAI(...)` ตามตาราง — `one_call()` ไม่ต้องแก้เลย
เพราะรูปแบบการเรียก API เหมือนกันทั้งสองฝั่ง (ตรวจแล้ว ข้อ 3)

`--backend` ค่า default คือ `openrouter` เพื่อไม่ให้พฤติกรรมเดิมเปลี่ยน

### 5.2 ลิสต์โมเดลต่อ backend

`DEFAULT_MODELS` เปลี่ยนจาก list เป็น dict คีย์ตามชื่อ backend:

```python
DEFAULT_MODELS = {
    "openrouter": ["anthropic/claude-opus-5", "openai/gpt-5.6-sol",
                   "google/gemini-3.8-flash", "qwen/qwen3.8-max"],
    "ollama": ["qwen3:latest", "llama3:8b", "deepseek-r1:latest"],
}
```

`suites/<ชื่อ>/models.json` ใช้โครงเดียวกัน (dict คีย์ตาม backend) — ตอนนี้ยังไม่มี suite ไหนสร้าง
ไฟล์นี้ จึงเปลี่ยน schema ได้โดยไม่กระทบของเดิม

โมเดล `:cloud` ถือเป็น backend `ollama` เหมือนกัน (ยิงผ่าน endpoint เดียวกัน ต่างแค่ tag) แต่
**ไม่ใส่ใน default** เพราะต้อง `ollama pull` tag ปัจจุบันก่อน ให้ใส่ผ่าน `models.json` หรือ `--models`

### 5.3 Concurrency

`MAX_WORKERS` ที่เป็นค่าคงที่เดียว ย้ายไปเป็น `workers` ในตาราง `BACKENDS`
เหตุผลที่ ollama ตั้งเป็น 1: โมเดล 8B กินราว 5 GB ยิงขนาน 4 ตัวบน RAM 16 GB จะ swap และช้ากว่าเดิม
อีกทั้ง ollama serialize request ต่อโมเดลอยู่แล้วโดย default ขนานไปก็ไม่ได้ throughput เพิ่ม

`REQUEST_TIMEOUT` คงไว้ที่ 600 วินาที — จากที่วัดจริง เคสที่ prompt ยาวกับโมเดล reasoning น่าจะอยู่
ราว 4–6 นาที ยังไม่ชนเพดาน

### 5.4 ชื่อโฟลเดอร์ผลลัพธ์และการติดป้าย

`run_dir()` เพิ่ม backend เข้าไปใน slug โดยแปลงชื่อโมเดลสองขั้น: `/` → `__` (ของเดิมทำอยู่แล้ว)
และเพิ่ม `:` → `-` (`:` ใช้ได้ในระดับ POSIX แต่ Finder บน macOS แสดงเป็น `/` ทำให้ชื่ออ่านสับสน):

```
results/2026-09-09__catfood__ollama__qwen3-latest/
results/2026-09-09__catfood__openrouter__anthropic__claude-opus-5/
```

`.meta.json` เพิ่มสองฟิลด์: `backend` และ `finish_reason`
`cmd_report()` อ่าน backend จาก slug มาแสดงเป็นคอลัมน์ → ได้ตารางเดียวที่บอกได้ว่าแถวไหน lane ไหน
ตรงตามหลัก MODEL_EVAL.md §12/§13 ที่ห้ามเทียบข้ามเงื่อนไขการรันแบบไม่รู้ตัว

### 5.5 Preflight check

เช็คครั้งเดียวก่อนเข้าลูปงาน ถ้าไม่ผ่านให้จบทันทีด้วยข้อความเดียว แทนที่จะปล่อยให้พังทีละงาน
(รันที่แล้วเสีย 48 งานไปกับ error เดียวกัน กว่าจะรู้ว่าเครดิตหมด):

- **ollama:** `GET /api/tags` — ต่อไม่ติด → บอกว่า `ollama ไม่ได้รันอยู่ ลอง ollama serve`
  ต่อติดแล้วเทียบ tag ที่ขอกับที่มีจริง → ไม่ตรง → บอกว่ามี tag อะไรให้เลือกบ้าง
- **openrouter:** `GET /api/v1/key` เพื่อดูเครดิตคงเหลือ แล้วพิมพ์ยอดออกมาให้เห็นก่อนเริ่มเสมอ
  ถ้าเครดิตคงเหลือ ≤ 0 ให้จบทันที (ไม่ต้องเดาว่าพอสำหรับกี่เคส เพราะราคาต่อ token ต่างกันตามโมเดล
  — แค่ยอดคงเหลือกับจำนวนงานที่จะยิงก็พอให้คนตัดสินใจเองได้ว่าจะเดินต่อไหม)

### 5.6 `max_tokens` และการดักคำตอบที่ถูกตัด

เพิ่มค่าคงที่ `MAX_TOKENS = 4000` ส่งไปกับทุก request พร้อม flag `--max-tokens` ให้ override

**กับดักที่ต้องอุดพร้อมกัน:** ถ้าคำตอบถูกตัดกลางคันแล้วเราให้ 0 ในเกณฑ์ที่โมเดลยังไม่ทันเขียนถึง
เท่ากับให้คะแนนผิดเพราะ harness ไม่ใช่เพราะโมเดล จึงต้อง:

1. บันทึก `finish_reason` ลง `.meta.json` ทุกครั้ง
2. เตือนบน stdout เมื่อค่าเป็น `length` เพื่อให้คนตรวจรู้ว่าไฟล์ไหนโดนตัด

## 6. เกณฑ์ตรวจรับ

1. `run catfood --backend ollama --cases e08` ได้ไฟล์ `.md` จริง 1 ไฟล์ (e08 prompt สั้นสุด 116 ตัวอักษร)
2. โฟลเดอร์ออกมาเป็น `2026-09-09__catfood__ollama__qwen3-latest` และ `.meta.json` มี `backend` กับ `finish_reason`
3. `report` แสดงคอลัมน์ backend แยก lane ได้
4. รันคำสั่งเดิมซ้ำ → ขึ้น `skip` ทุกงาน (resume ยังทำงานเหมือนเดิม)
5. สั่ง tag ที่ไม่มีอยู่จริง → จบด้วยข้อความเดียวที่บอกว่ามี tag อะไรบ้าง ไม่ใช่ error ซ้ำทุกงาน
6. `run catfood` เฉย ๆ (ไม่ใส่ `--backend`) ยังยิง OpenRouter เหมือนเดิม ไม่มีอะไรพัง

## 7. เอกสารที่ต้องอัปเดตพร้อมกัน

- [`MANUAL.md`](../../../MANUAL.md) — หัวข้อ local backend: วิธีเช็คว่า ollama รันอยู่, ดู tag ที่มี, ตัวอย่างคำสั่ง
- [`CLAUDE.md`](../../../CLAUDE.md) — หัวข้อ "สถานะ" เพิ่มบรรทัดว่ารองรับ local backend แล้ว
  และหัวข้อ "คำสั่ง" เพิ่มตัวอย่าง `--backend ollama`
- `.env.example` ไม่ต้องแก้ (ollama ไม่ใช้คีย์)

## 8. ความเสี่ยงที่รู้ตัวอยู่

- **คุณภาพคำตอบ:** เคส e01–e09 ออกแบบมาจับ failure ของโมเดลระดับบนสุด โมเดล 8B จะทำได้แย่ในเกือบทุกเคส
  ผลที่ได้ใช้ทดสอบว่า harness ทำงานครบวงจร ไม่ใช่ baseline สำหรับตัดสินใจเลือกโมเดลใช้งานจริง
- **tag ที่ retire:** โมเดล `:cloud` มีวันหมดอายุ (สองตัวที่โหลดไว้ตายไปแล้ว) preflight ข้อ 5.5
  จะจับได้ก่อนรันแต่ต้องไป pull ตัวใหม่เอง
- **ความเร็ว:** 12 เคส × 3 โมเดล ที่ worker=1 อาจกินเวลาเป็นชั่วโมง วางแผนเวลาเผื่อไว้
