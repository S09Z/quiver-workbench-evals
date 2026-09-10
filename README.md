# quiver-workbench-evals

สนามซ้อมส่วนตัวสำหรับทดสอบว่าโมเดลไหนใช้ทำงานจริงของเราได้ดีแค่ไหน

ดูรายละเอียดใน [CLAUDE.md](CLAUDE.md)

## ติดตั้ง

```bash
poetry install
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

## ใช้งาน

```bash
python harness/run.py init <suite>
python harness/run.py run <suite>
python harness/run.py report
```
