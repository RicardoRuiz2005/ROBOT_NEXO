from gtts import gTTS
import threading, os, tempfile

def hablar(msg, lang='es'):
    def _play():
        try:
            tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
            gTTS(msg, lang=lang).save(tmp)
            os.system(f"mpg123 {tmp} > /dev/null 2>&1")
        finally:
            try: os.remove(tmp)
            except: pass
    threading.Thread(target=_play, daemon=True).start()
