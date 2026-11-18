import os, re, glob, base64, subprocess, requests, yt_dlp
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
SERVER_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

HTML_UI = """
<!DOCTYPE html>
<html lang="my">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RedNote မြန်မာဘာသာပြန်</title>
    <style>
        body { font-family: sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 16px; }
        .container { max-width: 600px; margin: auto; }
        h2 { color: #ff2442; text-align: center; margin-bottom: 6px; }
        .badge { text-align: center; font-size: 12px; color: #10b981; margin-bottom: 18px; font-weight: bold; }
        .card { background: #1e293b; padding: 16px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 6px; }
        input, textarea, select { width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 12px; border-radius: 8px; font-size: 14px; margin-bottom: 12px; }
        button { width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
        button:disabled { background: #64748b; }
        .copy-btn { background: #10b981; margin-top: 10px; }
        #status { text-align: center; font-size: 14px; color: #38bdf8; margin-top: 10px; word-break: break-word; }
        .or-divider { text-align: center; color: #64748b; font-size: 12px; margin: 8px 0; font-weight: bold; }
    </style>
</head>
<body>
<div class="container">
    <h2>✨ RedNote → မြန်မာဘာသာပြန်</h2>
    <div class="badge">🚀 VIP Edition (No API Key / No VPN Needed)</div>
    <div class="card">
        <label>🔗 နည်းလမ်း (၁) - RedNote Share Link ထည့်ရန်</label>
        <textarea id="urlInput" rows="2" placeholder="http://xhslink.com/... စာသားတွေပါရောပါလာလည်း ရပါတယ်"></textarea>
        
        <div class="or-divider">— သို့မဟုတ် —</div>
        
        <label>📁 နည်းလမ်း (၂) - ဖုန်းထဲက Video ဖိုင် တိုက်ရိုက်ရွေးရန်</label>
        <input type="file" id="videoFile" accept="video/*">
        
        <label>📝 ဘာသာပြန်ပုံစံ (Mode)</label>
        <select id="modeInput">
            <option value="bilingual">မူရင်းတရုတ်စာ + မြန်မာဘာသာပြန် ယှဉ်တွဲပြရန်</option>
            <option value="exact">မြန်မာဘာသာပြန် သီးသန့် (အစအဆုံး အပြည့်အစုံ)</option>
        </select>
        
        <button id="genBtn" onclick="generateScript()">⚡ ချက်ချင်း ဘာသာပြန်မယ်</button>
        <div id="status"></div>
    </div>

    <div class="card" id="resultCard" style="display:none;">
        <label>📝 ထွက်လာသော မြန်မာဘာသာပြန်</label>
        <textarea id="outputText" rows="16"></textarea>
        <button class="copy-btn" onclick="copyText()">📋 စာသားအားလုံး Copy ကူးမယ်</button>
    </div>
</div>

<script>
    async function generateScript() {
        const rawText = document.getElementById('urlInput').value.trim();
        const fileInput = document.getElementById('videoFile');
        const mode = document.getElementById('modeInput').value;
        const btn = document.getElementById('genBtn');
        const status = document.getElementById('status');

        if (!rawText && fileInput.files.length === 0) return alert('RedNote Link ထည့်ပါ (သို့မဟုတ်) Video ဖိုင်ရွေးပါ!');

        btn.disabled = true;
        document.getElementById('resultCard').style.display = 'none';

        const formData = new FormData();
        formData.append('mode', mode);

        if (fileInput.files.length > 0) {
            formData.append('video', fileInput.files[0]);
            status.innerText = '⚡ ဗီဒီယိုထဲက စကားပြောနဲ့ စာတန်းတွေကို ဘာသာပြန်နေပါသည်...';
        } else {
            formData.append('text', rawText);
            status.innerText = '⚡ RedNote ဗီဒီယိုကို ဆွဲယူပြီး ဘာသာပြန်နေပါသည်...';
        }

        try {
            const res = await fetch('/process', { method: 'POST', body: formData });
            const data = await res.json();
            if (data.error) {
                status.innerText = '❌ Error: ' + data.error;
            } else {
                status.innerText = '✅ အပြည့်အစုံ ဘာသာပြန်ပြီးပါပြီ!';
                document.getElementById('outputText').value = data.script;
                document.getElementById('resultCard').style.display = 'block';
                fileInput.value = '';
            }
        } catch (e) {
            status.innerText = '❌ ချိတ်ဆက်မှု အဆင်မပြေပါ: ' + e;
        }
        btn.disabled = false;
    }

    function copyText() {
        const out = document.getElementById('outputText');
        out.select();
        document.execCommand('copy');
        alert('Copy ကူးပြီးပါပြီ!');
    }
</script>
</body>
</html>
"""

def cleanup():
    for f in ['/tmp/raw_video.mp4', '/tmp/tiny_audio.mp3'] + glob.glob('/tmp/sub_*.jpg'):
        if os.path.exists(f): os.remove(f)

@app.route('/')
def home():
    return render_template_string(HTML_UI)

@app.route('/process', methods=['POST'])
def process_video():
    api_key = SERVER_GEMINI_KEY.strip()
    if not api_key:
        return jsonify({'error': 'Server တွင် GEMINI_API_KEY မထည့်ရသေးပါ။'})

    raw_text = request.form.get('text', '')
    mode = request.form.get('mode', 'bilingual')
    raw_path = '/tmp/raw_video.mp4'
    audio_path = '/tmp/tiny_audio.mp3'

    cleanup()

    try:
        if 'video' in request.files and request.files['video'].filename != '':
            request.files['video'].save(raw_path)
        else:
            urls = re.findall(r'https?://[^\s]+', raw_text)
            if not urls:
                return jsonify({'error': 'Link ရှာမတွေ့ပါ။'})
            ydl_opts = {
                'outtmpl': raw_path,
                'format': 'best[height<=480][ext=mp4]/best[ext=mp4]/best',
                'quiet': True,
                'concurrent_fragment_downloads': 8,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
                    'Referer': 'https://www.xiaohongshu.com/'
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(urls[0], download=True)

        if not os.path.exists(raw_path) or os.path.getsize(raw_path) == 0:
            return jsonify({'error': 'ဗီဒီယိုဖိုင် မတွေ့ပါ။'})

        subprocess.run(['ffmpeg', '-y', '-i', raw_path, '-vn', '-ar', '16000', '-ac', '1', '-b:a', '32k', audio_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffmpeg', '-y', '-i', raw_path, '-vf', 'fps=1/1.5,scale=540:-1', '-q:v', '7', '-vframes', '35', '/tmp/sub_%02d.jpg'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        format_rule = (
            "မူရင်း တရုတ်/အင်္ဂလိပ် စာကြောင်း တစ်ကြောင်းချင်းစီရဲ့ အောက်မှာ မြန်မာဘာသာပြန် တစ်ကြောင်းစီ ယှဉ်တွဲပြီး အစအဆုံး တစ်ကြောင်းမကျန် ရေးပေးပါ။ (ဥပမာ-\n🇨🇳 မူရင်းစာကြောင်း\n🇲🇲 မြန်မာဘာသာပြန်)"
            if mode == "bilingual" else
            "မူရင်း စာကြောင်းတိုင်းကို တစ်ကြောင်းချင်း အစဉ်လိုက် မြန်မာဘာသာသို့ အစအဆုံး တစ်ကြောင်းမကျန် ဘာသာပြန်ပေးပါ။ မြန်မာစာသီးသန့်ကိုပဲ ထုတ်ပေးပါ။"
        )

        prompt = f"""ပေးထားသော အသံဖိုင် (Audio) နှင့် ဗီဒီယို စာတန်းပုံရိပ်များ (Screenshots) ထဲတွင် ပါဝင်သမျှ ပြောစကားနှင့် စာတန်းအားလုံးကို တစ်ကြောင်းမှ မကျန်လှပ်ဘဲ မြန်မာဘာသာသို့ တိတိကျကျ ပြန်ဆိုပေးပါ။
- ဇာတ်ကြောင်းပြန် (Recap) ပုံစံ လုံးဝ မရေးရပါ။ အကျဉ်းချုံးခြင်း လုံးဝ မလုပ်ရပါ။ အပိုစာသား လုံးဝ မထည့်ရပါ။
- {format_rule}"""

        parts = [{"text": prompt}]
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            ab = open(audio_path, "rb").read()
            parts.append({"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(ab).decode('utf-8')}})

        for img_f in sorted(glob.glob('/tmp/sub_*.jpg')):
            ib = open(img_f, "rb").read()
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(ib).decode('utf-8')}})

        gen_res = {}
        for m_try in ["gemini-flash-lite-latest", "gemini-3.8-flash"]:
            gen_res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{m_try}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.1}},
                timeout=45
            ).json()
            if "candidates" in gen_res:
                break

        cleanup()

        if 'candidates' in gen_res:
            text_out = gen_res['candidates'][0]['content']['parts'][0].text
            return jsonify({'script': text_out})
        else:
            return jsonify({'error': str(gen_res)})

    except Exception as e:
        cleanup()
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
