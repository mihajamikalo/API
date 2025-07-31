from flask import Flask, request, send_file, jsonify, after_this_request
import yt_dlp
import os
import time

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return "🚀 API YouTube Downloader (POST + Qualité limitée, sans FFmpeg) prête !"

@app.route("/download", methods=["POST"])
def download_video():
    url = request.form.get("url")
    quality = request.form.get("quality", "best")

    if not url:
        return jsonify({"error": "❌ URL manquante"}), 400

    # ✅ Formats progressifs (vidéo+audio déjà combinés, pas besoin de FFmpeg)
    progressive_formats = {
        "best": "best[height<=720][vcodec!=vp9][ext=mp4]",   # max 720p, flux combiné
        "720p": "best[height<=720][vcodec!=vp9][ext=mp4]",   # flux progressif max 720p
        "480p": "best[height<=480][vcodec!=vp9][ext=mp4]",   # flux progressif 480p
        "360p": "best[height<=360][vcodec!=vp9][ext=mp4]",   # flux progressif 360p
        "audio": "bestaudio[ext=m4a]"                        # audio seulement
    }

    # ✅ Si l'utilisateur demande >720p, on refuse car FFmpeg est requis
    if quality not in progressive_formats:
        return jsonify({"error": "❌ Qualité non supportée sans FFmpeg. Max: 720p"}), 400

    selected_format = progressive_formats[quality]
    filename = f"yt_{int(time.time())}.mp4" if quality != "audio" else f"yt_{int(time.time())}.m4a"
    filepath = os.path.join(DOWNLOAD_DIR, filename)

    # ✅ yt-dlp options sans fusion (FFmpeg non requis)
    ydl_opts = {
        "outtmpl": filepath,
        "format": selected_format,
        "quiet": True,
        "merge_output_format": "mp4"
    }

    try:
        # ✅ Téléchargement direct d’un flux progressif
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Vérification si le format choisi est DASH (audio/vidéo séparés)
            if info.get("requested_formats"):
                return jsonify({"error": "❌ Cette qualité nécessite FFmpeg pour fusionner audio/vidéo."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # ✅ Nettoyage du fichier après envoi
    @after_this_request
    def cleanup(response):
        try:
            # Attendre que le fichier soit bien fermé avant suppression
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"✅ Fichier supprimé: {filepath}")
        except Exception as e:
            print(f"⚠️ Impossible de supprimer {filepath}: {e}")
        return response

    # Utilise conditional=False pour éviter que Flask garde le fichier ouvert
    return send_file(filepath, as_attachment=True, conditional=False)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
