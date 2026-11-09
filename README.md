# تنزيل فيديو مصرح به من يوتيوب

هذا المشروع يقرأ رابط الفيديو من `VIDEO_URL` في ملف `.env` وينزله إلى مجلد `downloads/` باستخدام `yt-dlp` ونسخة FFmpeg التي توفرها حزمة `imageio-ffmpeg`. يعرض الدقات المتاحة، ثم يختار دقة عشوائية منها ويحمّل أفضل مسار فيديو بهذه الدقة مع مسار الصوت.

استخدمه فقط مع فيديو تملكه أو لديك إذن واضح بتنزيله، والتزم بحقوق النشر وشروط يوتيوب والقوانين المحلية.

## التشغيل على Wispbyte

لا تحتاج إلى Git LFS ولا إلى `sudo`. اجعل متغيرات الاستضافة كالآتي:

```text
AUTO_UPDATE=1
PY_FILE=downloader.py
REQUIREMENTS_FILE=requirements.txt
PY_PACKAGES=
```

أمر التشغيل:

```bash
if [[ -d .git ]] && [[ "${AUTO_UPDATE}" == "1" ]]; then git pull --ff-only; fi
if [[ -n "${PY_PACKAGES}" ]]; then pip install -U --prefix .local ${PY_PACKAGES}; fi
if [[ -f "/home/container/${REQUIREMENTS_FILE}" ]]; then pip install -U --prefix .local -r "/home/container/${REQUIREMENTS_FILE}"; fi
export PYTHONPATH="/home/container/.local/lib/python3.14/site-packages:${PYTHONPATH}"
exec /usr/local/bin/python /home/container/${PY_FILE}
```

ضع الرابط داخل `/home/container/.env`:

```env
VIDEO_URL=https://m.youtube.com/watch?v=yNkdwvFXSOc
OUTPUT_DIR=downloads
MAX_RETRIES=3
SOCKET_TIMEOUT=30
```

في أول تشغيل، ستقوم Wispbyte بتثبيت `yt-dlp` و`imageio-ffmpeg` من `requirements.txt`. لا تستخدم ملفات `bin/` القديمة من الإصدارات السابقة؛ تم حذفها لتجنب مشكلة Git LFS و`Exec format error`.

## إعدادات اختيارية

- `OUTPUT_DIR`: مجلد الحفظ، والافتراضي `downloads`.
- `FORMAT`: محدد أولي لـ yt-dlp، والاختيار النهائي يتم عشوائيًا من الدقات المتاحة.
- `MERGE_FORMAT`: صيغة الدمج، والافتراضي `mp4`.
- `MAX_RETRIES`: عدد محاولات إعادة الاتصال، والافتراضي `3`.
- `SOCKET_TIMEOUT`: مهلة الشبكة بالثواني، والافتراضي `30`.

## الحقوق والشروط

إذا لم يكن لديك إذن لتنزيل الفيديو، فلا تشغّل البرنامج عليه. لا يؤتمت هذا المشروع موقع RaiLoad ولا يستدعي نقاط النهاية الخاصة به.
