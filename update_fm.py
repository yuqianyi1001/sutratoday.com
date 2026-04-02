import re

file_path = "content/sutras-raw/T0221-007.md"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_fm = """---
title: 放光般若經 卷第七
short_title: 放光般若經卷七
slug: T0221-007
volume_label: 卷第七
cbeta_source: https://cbetaonline.dila.edu.tw/T08n0221_007
translation_status: translated
review_status: unreviewed
updated_at: 2026-04-01
summary: 本卷主要论述了受持、讽诵、演说般若波罗蜜的巨大现世功德与出世间功德，强调般若波罗蜜为诸佛之母、万法之源，其价值远胜于供养舍利。
tags: 般若,功德,舍利,如来,一切种智
translated_by: gemini-2.0-flash
---"""

content = re.sub(r'---.*?---', new_fm, content, count=1, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
