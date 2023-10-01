# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import *
import sys
import os
from werkzeug.utils import secure_filename
from vosk import Model, KaldiRecognizer, SetLogLevel
from pydub import AudioSegment
import uuid
import requests

#TEMPLATE_DIR = os.path.abspath('../templates')
#STATIC_DIR = os.path.abspath('../static')
# app = Flask(__name__) # to make the app run without any
#app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
UPLOAD_FOLDER = 'static/'
ALLOWED_EXTENSIONS = {"wav","mp3"}
LIBRE_TRANSLATE_URL = "http://localhost:5001/translate"
LANGUAGES = ["en", "es", "fr", "de", "zh", "ja", "ru", "it"]  # Add more languages as needed

app = Flask(__name__,template_folder="template/",static_folder="static/")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

#@app.route('/output/<path:filepath>')
#def stater(filepath):
#    return send_from_directory('output', filepath)
@app.route('/',methods=['GET', 'POST'])
def homePage():
    return render_template("index.html",output="",languages=LANGUAGES,)

@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def htmloader(text,inputaudio,outputaudio):
    x = ""
    x+="Utterance: <p>"+text+"</p><br>"
    x+="Original:<br>"
    x+="<audio controls>"
    x+="  <source src='"+inputaudio+"' type='audio/"+inputaudio.rsplit('.', 1)[1].lower()+"'>"
    x+="</audio><br>"
    x+="Cloned Utterance:<br>"
    x+="<audio controls>"
    x+="  <source src='"+str(outputaudio)+"' type='audio/wav'>"
    x+="</audio><br>"
    return x

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def upload_file():
    fil = []
    if request.method == 'POST':
        f = request.files['file']
        if allowed_file(f.filename):
            f.save(UPLOAD_FOLDER+secure_filename(f.filename))
            fil.append("File uploaded successfully")
            fil.append(UPLOAD_FOLDER+secure_filename(f.filename))
            return fil
        else:
            fil.append("Not An Expected File")
            return fil



@app.route('/process',methods=['GET', 'POST'])
def Voice_clone():
    legoutput = upload_file()
    lig = "This is a demo utterance. This will work when you do not add any utterance."
    if request.method == 'POST':
        lig = request.form["textarea"]
    print(str(lig))
    #return mainpage()
    if str(legoutput)=="None":
        return render_template("index.html",output="")
    else:
        from encoder.params_model import model_embedding_size as speaker_embedding_size
        from utils.argutils import print_args
        from synthesizer.inference import Synthesizer
        from encoder import inference as encoder
        from vocoder import inference as vocoder
        from pathlib import Path
        import numpy as np
        import soundfile as sf
        import librosa
        import argparse
        import torch
        try:
            parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
            parser.add_argument("-e", "--enc_model_fpath", type=Path,default="encoder/saved_models/pretrained.pt")
            parser.add_argument("-s", "--syn_model_dir", type=Path,default="synthesizer/saved_models/logs-pretrained/")
            parser.add_argument("-v", "--voc_model_fpath", type=Path,default="vocoder/saved_models/pretrained/pretrained.pt")
            parser.add_argument("--low_mem", action="store_true")
            #parser.add_argument("--no_sound", action="store_true")
            args = parser.parse_args()
            print_args(args, parser)
            #if not args.no_sound:
            #    import sounddevice as sd
            encoder.load_model(args.enc_model_fpath)
            synthesizer = Synthesizer(args.syn_model_dir.joinpath("taco_pretrained"), low_mem=args.low_mem)
            vocoder.load_model(args.voc_model_fpath)
            num_generated = 0
            in_fpath = legoutput[1]
            print(str(in_fpath))
            preprocessed_wav = encoder.preprocess_wav(in_fpath)
            original_wav, sampling_rate = librosa.load(in_fpath)
            preprocessed_wav = encoder.preprocess_wav(original_wav, sampling_rate)
            embed = encoder.embed_utterance(preprocessed_wav)
            print("Created the embedding")
            text = str(lig)
            texts = [text]
            embeds = [embed]
            specs = synthesizer.synthesize_spectrograms(texts, embeds)
            spec = specs[0]
            print("Created the mel spectrogram")
            print("Synthesizing the waveform:")
            generated_wav = vocoder.infer_waveform(spec)
            generated_wav = np.pad(generated_wav, (0, synthesizer.sample_rate), mode="constant")
            #if not args.no_sound:
            #    sd.stop()
            #    sd.play(generated_wav, synthesizer.sample_rate)
            fpath = "static/output.wav"
            print(generated_wav.dtype)
            # librosa.output.write_wav(fpath, generated_wav.astype(np.float32),synthesizer.sample_rate)
            sf.write(fpath, generated_wav.astype(np.float32), synthesizer.sample_rate, 'PCM_24')
            print("\nSaved output as %s\n\n" % fpath)
            return render_template("index.html",output=htmloader(text,legoutput[1],fpath), languages=LANGUAGES, text = text)
        except Exception as e:
            return render_template("index.html",output="Caught exception: %s" % repr(e), languages=LANGUAGES, text = text)
    #return xieon
@app.route("/translate", methods=["GET", "POST"])
def translate():
    translation = ""
    if request.method == "POST":
        source_lang = request.form.get("source_lang")
        target_lang = request.form.get("target_lang")
        text = request.form.get("text")
        data = {
            "q": text,
            "source": source_lang,
            "target": target_lang
        }
        response = requests.post(LIBRE_TRANSLATE_URL, data=data)
        translation = response.json().get("translatedText", "")

    return render_template("index.html", languages=LANGUAGES, translation=translation, text = text)


# Load the Vosk model
model = Model(lang="en-us")
SetLogLevel(0)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONST = {'mp3', 'wav', 'flac', 'ogg', 'm4a'}

def allowed_filet(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONST

@app.route('/transcribe', methods=['POST'])
def recognize_speech():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_filet(file.filename):
        return jsonify({"error": "Unsupported file format"}), 400

    if file and allowed_filet(file.filename):
        # Convert audio file to WAV format using ffmpeg
        audio = AudioSegment.from_file(file, format=file.filename.split('.')[-1])
        audio = audio.set_channels(1)  # Set to mono
        audio = audio.set_frame_rate(16000)  # Set frame rate to 16,000 Hz

        # Generate a unique filename for the temporary WAV file
        temp_filename = f"temp_{uuid.uuid4()}.wav"
        audio.export(temp_filename, format="wav")

        with open(temp_filename, 'rb') as f:
            # Read the word list from a file
            # with open('dicionaryEng.txt', 'r') as file:
            #     words = file.read().replace('\n', ' ')
            # You can also specify the possible word list
            #rec = KaldiRecognizer(model, 16000, "zero oh one two three four five six seven eight nine")    
            rec = KaldiRecognizer(model, 16000)
            f.seek(44)  # skip header
            results = []
            while True:
                data = f.read(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    results.append(res["text"])

            final_result = json.loads(rec.FinalResult())
            results.append(final_result["text"])

        # Remove the temporary WAV file after processing
        os.remove(temp_filename)

        print({"results": results})
        return render_template("index.html", transcription=results[0],languages=LANGUAGES)

    return jsonify({"error": "An error occurred during processing"}), 500
# main driver function
if __name__ == '__main__':

    # run() method of Flask class runs the application
    # on the local development server.
    app.run()